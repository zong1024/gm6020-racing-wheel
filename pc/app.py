from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from serial.tools import list_ports

from bridge import Config, SerialBridge, Telemetry

CONFIG_PATH = Path(__file__).with_name("config.json")

app = Flask(__name__)
app.config["SECRET_KEY"] = "gm6020-racing-wheel"
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

cfg = Config.load(CONFIG_PATH)
bridge: SerialBridge | None = None
telemetry = Telemetry()
calibration_points: list[float] = []
state_lock = threading.Lock()
telemetry_task_started = False


def available_ports() -> list[str]:
    ports = [port.device for port in list_ports.comports()]
    if cfg.serial_port and cfg.serial_port not in ports:
        ports.insert(0, cfg.serial_port)
    return ports


def telemetry_payload() -> dict[str, Any]:
    with state_lock:
        return {
            "angle_deg": telemetry.angle_deg,
            "target_deg": telemetry.target_deg,
            "rpm": telemetry.rpm,
            "torque_current": telemetry.torque_current,
            "state": telemetry.state,
            "connected": bridge is not None and bridge.is_connected,
        }


def config_payload() -> dict[str, Any]:
    return {
        "serial_port": cfg.serial_port,
        "baudrate": cfg.baudrate,
        "max_angle_deg": cfg.max_angle_deg,
        "deadzone_deg": cfg.deadzone_deg,
        "kp": cfg.kp,
        "ki": cfg.ki,
        "kd": cfg.kd,
        "ports": available_ports(),
    }


def on_telemetry(update: Telemetry) -> None:
    global telemetry
    with state_lock:
        telemetry = Telemetry(
            angle_deg=update.angle_deg,
            target_deg=update.target_deg,
            rpm=update.rpm,
            torque_current=update.torque_current,
            state=update.state,
        )


def telemetry_loop() -> None:
    while True:
        socketio.emit("telemetry", telemetry_payload())
        socketio.sleep(0.05)  # 20 Hz browser updates


@app.route("/")
def index() -> str:
    return render_template_string(PAGE)


@socketio.on("connect")
def handle_connect() -> None:
    global telemetry_task_started
    emit("config", config_payload())
    emit("telemetry", telemetry_payload())
    if not telemetry_task_started:
        telemetry_task_started = True
        socketio.start_background_task(telemetry_loop)


@socketio.on("refresh_ports")
def handle_refresh_ports() -> None:
    emit("ports", {"ports": available_ports()})


@socketio.on("connect_serial")
def handle_connect_serial(data: dict[str, Any]) -> None:
    global bridge
    requested_port = str(data.get("serial_port", cfg.serial_port)).strip()
    if not requested_port:
        emit("status", {"ok": False, "message": "Select a serial port first."})
        return
    cfg.serial_port = requested_port
    try:
        if bridge:
            bridge.close()
        bridge = SerialBridge(cfg, on_telemetry)
        bridge.connect()
        emit("config", config_payload())
        socketio.emit("status", {"ok": True, "message": f"Connected to {cfg.serial_port}."})
    except Exception as exc:
        bridge = None
        with state_lock:
            telemetry.state = "DISCONNECTED"
        emit("status", {"ok": False, "message": f"Connection failed: {exc}"})


@socketio.on("disconnect_serial")
def handle_disconnect_serial() -> None:
    global bridge
    if bridge:
        bridge.close()
        bridge = None
    with state_lock:
        telemetry.state = "DISCONNECTED"
    socketio.emit("status", {"ok": True, "message": "Disconnected."})


@socketio.on("pid_update")
def handle_pid_update(data: dict[str, Any]) -> None:
    try:
        cfg.kp = float(data["kp"])
        cfg.ki = float(data["ki"])
        cfg.kd = float(data["kd"])
    except (KeyError, TypeError, ValueError):
        emit("status", {"ok": False, "message": "Invalid PID payload."})
        return
    if bridge:
        bridge.send_pid()
    socketio.emit("config", config_payload())


@socketio.on("target_update")
def handle_target_update(data: dict[str, Any]) -> None:
    try:
        target = float(data["target_deg"])
    except (KeyError, TypeError, ValueError):
        emit("status", {"ok": False, "message": "Invalid target angle."})
        return
    if bridge:
        bridge.set_target_angle(target)


@socketio.on("center")
def handle_center() -> None:
    if bridge:
        bridge.center()
        emit("status", {"ok": True, "message": "Center command sent."})
    else:
        emit("status", {"ok": False, "message": "Connect before centering."})


@socketio.on("record_limit")
def handle_record_limit() -> None:
    with state_lock:
        calibration_points.append(abs(telemetry.angle_deg))
    cfg.max_angle_deg = max(calibration_points, default=cfg.max_angle_deg)
    socketio.emit("config", config_payload())
    emit("status", {"ok": True, "message": f"Recorded limit: ±{cfg.max_angle_deg:.2f}°."})


@socketio.on("save_config")
def handle_save_config(data: dict[str, Any] | None = None) -> None:
    if data and data.get("serial_port"):
        cfg.serial_port = str(data["serial_port"])
    cfg.save(CONFIG_PATH)
    emit("status", {"ok": True, "message": "Configuration saved."})


@socketio.on("load_config")
def handle_load_config() -> None:
    global cfg
    loaded = Config.load(CONFIG_PATH)
    cfg.serial_port = loaded.serial_port
    cfg.baudrate = loaded.baudrate
    cfg.max_angle_deg = loaded.max_angle_deg
    cfg.deadzone_deg = loaded.deadzone_deg
    cfg.kp = loaded.kp
    cfg.ki = loaded.ki
    cfg.kd = loaded.kd
    cfg.telemetry_hz = loaded.telemetry_hz
    if bridge:
        bridge.send_pid()
    socketio.emit("config", config_payload())
    emit("status", {"ok": True, "message": "Configuration loaded."})


PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GM6020 Racing Wheel</title>
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070b12;
      --panel: rgba(16, 23, 35, 0.92);
      --panel-2: #111827;
      --line: rgba(255,255,255,0.09);
      --text: #e5edf7;
      --muted: #93a4b8;
      --accent: #ff4d1a;
      --accent-2: #ffb347;
      --good: #20d17a;
      --bad: #ff5d73;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 10%, rgba(255,77,26,.18), transparent 30%),
        radial-gradient(circle at 90% 0%, rgba(255,179,71,.12), transparent 28%),
        linear-gradient(180deg, #0a0f18 0%, var(--bg) 100%);
    }
    .shell { max-width: 1200px; margin: 0 auto; padding: 28px; }
    header { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:20px; }
    h1 { margin:0; letter-spacing:.08em; font-size: clamp(1.2rem, 2vw, 1.8rem); }
    .status { display:flex; align-items:center; gap:10px; color:var(--muted); }
    .dot { width:11px; height:11px; border-radius:999px; background:var(--bad); box-shadow:0 0 18px var(--bad); }
    .dot.connected { background:var(--good); box-shadow:0 0 18px var(--good); }
    .grid { display:grid; grid-template-columns: 1.1fr .9fr; gap:18px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:20px; box-shadow:0 18px 60px rgba(0,0,0,.28); }
    .hero { display:grid; grid-template-columns: 1fr 1fr; gap:18px; align-items:center; }
    .wheel-wrap { display:grid; place-items:center; min-height:320px; }
    .wheel {
      width:min(280px, 72vw); aspect-ratio:1; border-radius:50%;
      border:18px solid #202938; position:relative;
      box-shadow: inset 0 0 0 4px #0a0f18, 0 0 0 1px rgba(255,255,255,.06), 0 20px 50px rgba(0,0,0,.35);
      transition: transform .08s linear;
    }
    .wheel::before, .wheel::after { content:""; position:absolute; background:#202938; left:50%; top:50%; transform:translate(-50%,-50%); border-radius:999px; }
    .wheel::before { width:18px; height:74%; }
    .wheel::after { width:74%; height:18px; }
    .hub { position:absolute; inset:50%; transform:translate(-50%,-50%); width:74px; height:74px; border-radius:50%; background:linear-gradient(135deg,var(--accent),#8b250b); border:4px solid #111827; z-index:2; }
    .readout { font-size: clamp(2.4rem, 6vw, 4rem); font-weight:700; line-height:1; }
    .sub { color:var(--muted); margin-top:8px; }
    .telemetry { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:18px; }
    .metric { background:var(--panel-2); border:1px solid var(--line); border-radius:16px; padding:14px; }
    .metric span { display:block; color:var(--muted); font-size:.8rem; margin-bottom:4px; }
    .metric strong { font-size:1.25rem; }
    .stack { display:grid; gap:16px; }
    label { display:flex; justify-content:space-between; color:var(--muted); margin-bottom:8px; }
    input[type="range"] { width:100%; accent-color:var(--accent); }
    select { width:100%; background:#0c1320; color:var(--text); border:1px solid var(--line); border-radius:12px; padding:12px; }
    .row { display:flex; gap:10px; flex-wrap:wrap; }
    button {
      border:1px solid var(--line); border-radius:12px; padding:11px 14px;
      color:var(--text); background:#151e2d; cursor:pointer;
    }
    button.primary { background:linear-gradient(135deg,var(--accent),#c63814); border:none; }
    button:hover { filter:brightness(1.08); }
    .message { min-height:20px; color:var(--muted); font-size:.92rem; }
    @media (max-width: 860px) { .grid, .hero { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<div class="shell">
  <header>
    <div>
      <h1>GM6020 RACING WHEEL</h1>
      <div class="sub">Web telemetry + live tuning console</div>
    </div>
    <div class="status"><span id="dot" class="dot"></span><span id="connectionText">Disconnected</span></div>
  </header>

  <main class="grid">
    <section class="panel hero">
      <div class="wheel-wrap"><div id="wheel" class="wheel"><div class="hub"></div></div></div>
      <div>
        <div id="angle" class="readout">0.00°</div>
        <div class="sub">Current steering angle</div>
        <div class="telemetry">
          <div class="metric"><span>Target</span><strong id="target">0.00°</strong></div>
          <div class="metric"><span>RPM</span><strong id="rpm">0</strong></div>
          <div class="metric"><span>Torque</span><strong id="torque">0</strong></div>
          <div class="metric"><span>State</span><strong id="state">DISCONNECTED</strong></div>
        </div>
      </div>
    </section>

    <section class="panel stack">
      <div>
        <label><span>Serial port</span></label>
        <div class="row">
          <select id="port"></select>
          <button id="refreshPorts">Refresh</button>
          <button id="connect" class="primary">Connect</button>
          <button id="disconnect">Disconnect</button>
        </div>
      </div>

      <div>
        <label><span>Kp</span><strong id="kpValue"></strong></label>
        <input id="kp" type="range" min="0" max="300" step="0.1">
      </div>
      <div>
        <label><span>Ki</span><strong id="kiValue"></strong></label>
        <input id="ki" type="range" min="0" max="50" step="0.01">
      </div>
      <div>
        <label><span>Kd</span><strong id="kdValue"></strong></label>
        <input id="kd" type="range" min="0" max="20" step="0.01">
      </div>
      <div>
        <label><span>Manual target</span><strong id="manualTargetValue">0.00°</strong></label>
        <input id="manualTarget" type="range" min="-360" max="360" step="0.1" value="0">
      </div>

      <div class="row">
        <button id="center" class="primary">Center</button>
        <button id="recordLimit">Record limit</button>
        <button id="saveConfig">Save config</button>
        <button id="loadConfig">Load config</button>
      </div>
      <div id="message" class="message"></div>
    </section>
  </main>
</div>
<script>
  const socket = io();
  const $ = (id) => document.getElementById(id);
  const inputs = ["kp", "ki", "kd"];

  function setPorts(ports, selected) {
    $("port").innerHTML = "";
    ports.forEach((port) => {
      const option = document.createElement("option");
      option.value = port;
      option.textContent = port;
      option.selected = port === selected;
      $("port").appendChild(option);
    });
  }

  function pushPid() {
    socket.emit("pid_update", { kp: +$("kp").value, ki: +$("ki").value, kd: +$("kd").value });
  }

  inputs.forEach((id) => {
    $(id).addEventListener("input", () => {
      $(id + "Value").textContent = (+$(id).value).toFixed(id === "kp" ? 1 : 2);
      pushPid();
    });
  });

  $("manualTarget").addEventListener("input", () => {
    $("manualTargetValue").textContent = (+$("manualTarget").value).toFixed(2) + "°";
    socket.emit("target_update", { target_deg: +$("manualTarget").value });
  });
  $("refreshPorts").onclick = () => socket.emit("refresh_ports");
  $("connect").onclick = () => socket.emit("connect_serial", { serial_port: $("port").value });
  $("disconnect").onclick = () => socket.emit("disconnect_serial");
  $("center").onclick = () => socket.emit("center");
  $("recordLimit").onclick = () => socket.emit("record_limit");
  $("saveConfig").onclick = () => socket.emit("save_config", { serial_port: $("port").value });
  $("loadConfig").onclick = () => socket.emit("load_config");

  socket.on("config", (cfg) => {
    setPorts(cfg.ports, cfg.serial_port);
    $("kp").value = cfg.kp; $("ki").value = cfg.ki; $("kd").value = cfg.kd;
    $("kpValue").textContent = (+cfg.kp).toFixed(1);
    $("kiValue").textContent = (+cfg.ki).toFixed(2);
    $("kdValue").textContent = (+cfg.kd).toFixed(2);
    $("manualTarget").min = -cfg.max_angle_deg;
    $("manualTarget").max = cfg.max_angle_deg;
  });
  socket.on("ports", ({ports}) => setPorts(ports, $("port").value));
  socket.on("status", ({ok, message}) => {
    $("message").textContent = message;
    $("message").style.color = ok ? "var(--good)" : "var(--bad)";
  });
  socket.on("telemetry", (t) => {
    $("angle").textContent = t.angle_deg.toFixed(2) + "°";
    $("target").textContent = t.target_deg.toFixed(2) + "°";
    $("rpm").textContent = t.rpm;
    $("torque").textContent = t.torque_current;
    $("state").textContent = t.state;
    $("wheel").style.transform = `rotate(${t.angle_deg}deg)`;
    $("dot").classList.toggle("connected", t.connected);
    $("connectionText").textContent = t.connected ? "Connected" : "Disconnected";
  });
</script>
</body>
</html>'''


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
