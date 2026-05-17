# GM6020 Racing Wheel / 赛车方向盘

A reference project for building a force-actuated steering wheel around a DJI GM6020 and Robomaster C Board (STM32F427): STM32 HAL firmware, a Python serial bridge, virtual gamepad output, and a browser-based tuning dashboard.

## Repository layout

```text
firmware/  STM32 application-layer C code and CMake target
pc/        Python serial bridge, WebUI, and config
docs/      Wiring and setup notes
```

## What is implemented

- GM6020 CAN command output on `0x1FF` and feedback parsing from `0x204`
- Multi-turn encoder tracking, RPM, and torque-current telemetry
- 1 kHz PID position loop for steering angle control
- UART command channel for live target angle and PID tuning
- Startup logical centering plus software travel limits at `±360°`
- Flask WebUI with live telemetry, animated steering wheel, PID sliders, center/calibration controls, and config save/load
- Virtual Xbox gamepad steering output via `vgamepad`

## Hardware

- DJI GM6020 motor
- Robomaster C Board / STM32F427
- 24 V supply suitable for the motor
- USB cable from board to PC
- CAN wiring between motor and board

See `docs/wiring.md` for the exact wiring sketch.

## Quick start

### Firmware

This repo intentionally keeps the firmware as a portable application layer rather than committing one specific CubeMX-generated board project. Generate the Robomaster C board support project, then integrate the sources under `firmware/`. The code expects:

- `CAN1` for the GM6020 bus
- `USART3` at `115200 8N1`
- STM32 HAL symbols such as `hcan1`, `huart3`, `MX_CAN1_Init`, and `MX_USART3_UART_Init`

Detailed steps are in `docs/setup.md`.

### PC app

```bash
cd pc
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
# then open http://127.0.0.1:5000 in your browser
```

Edit `pc/config.json` for COM port, angle range, deadzone, and starting PID values.


## WebUI

The PC app is now a single-page dark dashboard served by Flask-SocketIO. It streams telemetry to the browser at 20 Hz and sends PID updates, target-angle changes, centering, calibration, and config actions back over WebSocket without page reloads.

### Screenshots

Add screenshots here once the wheel is connected and running:

```text
docs/screenshots/dashboard.png
docs/screenshots/pid-tuning.png
```

## Control model

The wheel speaks a tiny serial protocol:

```text
A,30.0          # set target angle to +30 degrees
PID,120,0,2.5   # update Kp/Ki/Kd
CENTER          # capture current position as logical zero
```

The board streams telemetry back as:

```text
T,current_angle,target_angle,rpm,torque_current
```

The WebUI converts the measured wheel angle into the left X axis of a virtual Xbox controller, so racing games can bind it like a normal steering device.

## Safety notes

- Begin with the rim removed or the motor unloaded.
- A GM6020 can move violently if PID gains are poor or CAN frames are malformed.
- Software limits are not a substitute for a physical emergency stop.
- This project uses a *logical* center on startup; for true repeatable homing, add a sensor or mechanical homing fixture.

## Next useful upgrades

- Add a dedicated e-stop input and latch fault state
- Add force-feedback torque mode from game telemetry
- Add nonvolatile calibration storage in flash
- Add hardware center sensor for absolute homing
