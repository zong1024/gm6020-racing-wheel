# Setup guide

## 1. Firmware environment

The firmware workflow is now **Keil uVision5 (MDK-ARM) + STM32CubeMX**.

1. In STM32CubeMX, create an `STM32F427VGTx` project and save it under `firmware/STM32CubeMX/`.
2. Configure CAN1, USART3, the 168 MHz clock tree, and separate peripheral init files as described in `firmware/STM32CubeMX/README.md`.
3. Generate code for the **MDK-ARM** toolchain.
4. Open `firmware/MDK-ARM/GM6020_Racing_Wheel.uvprojx` in Keil uVision5.
5. Build and flash the target with ARM Compiler 6 / armclang.

The Keil project already references the application sources in `firmware/src/` and `firmware/include/`. CubeMX supplies the generated HAL headers, peripheral init files, interrupt handlers, and startup support under `firmware/STM32CubeMX/`.

Expected CubeMX symbols:

- `hcan1`, `MX_CAN1_Init()`
- `huart3`, `MX_USART3_UART_Init()`
- `MX_GPIO_Init()`
- generated HAL headers such as `main.h`, `can.h`, `usart.h`, and `gpio.h`

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
