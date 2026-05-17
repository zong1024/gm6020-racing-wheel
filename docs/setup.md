# Setup guide

## 1. Firmware

1. Create a Robomaster C / STM32F427 project in STM32CubeMX or your existing board support package.
2. Enable:
   - CAN1 at the bus speed used by the GM6020 network (commonly 1 Mbps in DJI ecosystems)
   - USART3 at 115200 8N1, RX interrupt enabled
   - 1 ms SysTick
3. Copy `firmware/include` and `firmware/src` into the generated project, or link the `wheel_app` target from `firmware/CMakeLists.txt`.
4. Ensure the generated project exposes `hcan1`, `huart3`, `MX_CAN1_Init`, `MX_USART3_UART_Init`, and `SystemClock_Config`.
5. Flash the board.

## 2. PC environment

```bash
cd pc
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python run_gui.py
```

For `vgamepad`, Windows may require the ViGEmBus driver before the virtual Xbox controller appears.

## 3. Serial protocol

PC -> board:
- `A,<angle_deg>` target angle, for example `A,25.0`
- `PID,<kp>,<ki>,<kd>` live tuning, for example `PID,120,0,2.5`
- `CENTER` capture the present wheel position as logical zero

Board -> PC:
- `STATE,CENTERING`
- `STATE,READY`
- `T,<angle_deg>,<target_deg>,<rpm>,<torque_current>`

## 4. Centering behavior

A GM6020 encoder gives shaft angle, not an absolute mechanical center. With no external limit switch or index sensor, the safest deterministic startup behavior is to wait for the wheel to settle, then capture the current physical position as logical zero. If you need a true repeatable mechanical center after every power cycle, add a center sensor or end-stop homing mechanism.

## 5. First tuning pass

1. Lift the wheel or remove the rim for first power-on.
2. Start with `Ki = 0`.
3. Increase `Kp` until the wheel tracks but begins to feel lively.
4. Add `Kd` until overshoot is acceptably damped.
5. Add a small `Ki` only if steady-state bias remains.

## 6. GUI calibration

After centering, rotate the wheel to each intended travel extreme and press `Record limit`.
The GUI keeps the largest absolute angle it has seen as the configured travel range; press
`Save config` when satisfied.
