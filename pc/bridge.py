from __future__ import annotations
import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import serial

try:
    import vgamepad as vg
except ImportError:  # graceful fallback for telemetry-only development
    vg = None


@dataclass
class Config:
    serial_port: str
    baudrate: int
    max_angle_deg: float
    deadzone_deg: float
    kp: float
    ki: float
    kd: float
    telemetry_hz: int

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        raw = json.loads(Path(path).read_text())
        return cls(
            serial_port=raw["serial_port"],
            baudrate=raw["baudrate"],
            max_angle_deg=raw["max_angle_deg"],
            deadzone_deg=raw["deadzone_deg"],
            kp=raw["pid"]["kp"],
            ki=raw["pid"]["ki"],
            kd=raw["pid"]["kd"],
            telemetry_hz=raw.get("telemetry_hz", 60),
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({
            "serial_port": self.serial_port,
            "baudrate": self.baudrate,
            "max_angle_deg": self.max_angle_deg,
            "deadzone_deg": self.deadzone_deg,
            "pid": {"kp": self.kp, "ki": self.ki, "kd": self.kd},
            "telemetry_hz": self.telemetry_hz,
        }, indent=2))


@dataclass
class Telemetry:
    angle_deg: float = 0.0
    target_deg: float = 0.0
    rpm: int = 0
    torque_current: int = 0
    state: str = "DISCONNECTED"


class VirtualPad:
    def __init__(self) -> None:
        self.pad = vg.VX360Gamepad() if vg else None

    def update_wheel(self, angle_deg: float, cfg: Config) -> None:
        if not self.pad:
            return
        if abs(angle_deg) < cfg.deadzone_deg:
            angle_deg = 0.0
        normalized = max(-1.0, min(1.0, angle_deg / cfg.max_angle_deg))
        self.pad.left_joystick_float(x_value_float=normalized, y_value_float=0.0)
        self.pad.update()


class SerialBridge:
    def __init__(self, cfg: Config, on_telemetry: Optional[Callable[[Telemetry], None]] = None) -> None:
        self.cfg = cfg
        self.on_telemetry = on_telemetry
        self.telemetry = Telemetry()
        self._serial: Optional[serial.Serial] = None
        self._reader: Optional[threading.Thread] = None
        self._writer: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._targets: "queue.Queue[float]" = queue.Queue(maxsize=1)
        self.pad = VirtualPad()
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open and self._running.is_set()

    def connect(self) -> None:
        self._serial = serial.Serial(self.cfg.serial_port, self.cfg.baudrate, timeout=0.05)
        self._running.set()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._reader.start()
        self._writer.start()
        self.send_pid()

    def close(self) -> None:
        self._running.clear()
        if self._serial:
            self._serial.close()
        self.telemetry.state = "DISCONNECTED"
        if self.on_telemetry:
            self.on_telemetry(self.telemetry)

    def send_pid(self) -> None:
        self._write_line(f"PID,{self.cfg.kp:.3f},{self.cfg.ki:.3f},{self.cfg.kd:.3f}")

    def center(self) -> None:
        self._write_line("CENTER")

    def set_target_angle(self, angle_deg: float) -> None:
        angle_deg = max(-self.cfg.max_angle_deg, min(self.cfg.max_angle_deg, angle_deg))
        while not self._targets.empty():
            try:
                self._targets.get_nowait()
            except queue.Empty:
                break
        try:
            self._targets.put_nowait(angle_deg)
        except queue.Full:
            pass

    def _write_line(self, line: str) -> None:
        if self._serial and self._serial.is_open:
            self._serial.write((line + "\n").encode())

    def _write_loop(self) -> None:
        period = 1.0 / max(1, self.cfg.telemetry_hz)
        last_target = 0.0
        while self._running.is_set():
            try:
                last_target = self._targets.get_nowait()
            except queue.Empty:
                pass
            self._write_line(f"A,{last_target:.2f}")
            time.sleep(period)

    def _read_loop(self) -> None:
        assert self._serial is not None
        while self._running.is_set():
            try:
                line = self._serial.readline().decode(errors="ignore").strip()
            except serial.SerialException:
                self.telemetry.state = "DISCONNECTED"
                if self.on_telemetry:
                    self.on_telemetry(self.telemetry)
                break
            if not line:
                continue
            with self._lock:
                if line.startswith("STATE,"):
                    self.telemetry.state = line.split(",", 1)[1]
                elif line.startswith("T,"):
                    try:
                        _, angle, target, rpm, torque = line.split(",")
                        self.telemetry.angle_deg = float(angle)
                        self.telemetry.target_deg = float(target)
                        self.telemetry.rpm = int(rpm)
                        self.telemetry.torque_current = int(torque)
                        self.pad.update_wheel(self.telemetry.angle_deg, self.cfg)
                    except ValueError:
                        continue
                snapshot = Telemetry(
                    angle_deg=self.telemetry.angle_deg,
                    target_deg=self.telemetry.target_deg,
                    rpm=self.telemetry.rpm,
                    torque_current=self.telemetry.torque_current,
                    state=self.telemetry.state,
                )
            if self.on_telemetry:
                self.on_telemetry(snapshot)
