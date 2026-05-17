# STM32CubeMX setup for the Keil project

This repository now expects CubeMX to generate the board-support layer and Keil uVision5 to build the final image.

## 1. Create the project

1. In STM32CubeMX, start a new project for `STM32F427VGTx`.
2. Set **Toolchain / IDE** to **MDK-ARM**.
3. Save the project under `firmware/STM32CubeMX/`.
4. In **Project Manager > Code Generator**, enable **Generate peripheral initialization as a pair of '.c/.h' files per peripheral**. The Keil project expects `can.c`, `usart.c`, and `gpio.c` under `Core/Src`.

## 2. Clock tree

Use the Robomaster-style external crystal setup:

- RCC HSE: `Crystal/Ceramic Resonator`
- HSE frequency: `8 MHz`
- PLL source: `HSE`
- PLLM: `8`
- PLLN: `336`
- PLLP: `2`
- PLLQ: `7`
- SYSCLK: `168 MHz`
- AHB prescaler: `/1`
- APB1 prescaler: `/4` (`42 MHz`)
- APB2 prescaler: `/2` (`84 MHz`)

CubeMX should emit `SystemClock_Config()` with those values. Keep that generated function and copy it into `firmware/src/main.c` if you regenerate the project from scratch.

## 3. CAN1

Configure `CAN1` for the GM6020 bus:

- Mode: `Normal`
- Bit rate: `1 Mbit/s` for the usual DJI motor network
- NVIC: enable `CAN1 RX0 interrupt`
- Pins: use the MCU pins routed by your specific C-board revision. For STM32F427, `PD0 = CAN1_RX` and `PD1 = CAN1_TX` are the common mapping; confirm against the board schematic before committing hardware.

The external connector is labeled `CAN1_H` / `CAN1_L`; those are transceiver-side bus signals, not MCU GPIO names.

## 4. USART3

Configure `USART3` as:

- Mode: `Asynchronous`
- Baud rate: `115200`
- Word length: `8 Bits`
- Parity: `None`
- Stop bits: `1`
- NVIC: enable `USART3 global interrupt`

Use the board-routed USART3 pins from your schematic or existing BSP. The application expects CubeMX to expose `huart3`.

## 5. Code generation and file placement

After generating code:

- Keep CubeMX output in `firmware/STM32CubeMX/`.
- Open `firmware/MDK-ARM/GM6020_Racing_Wheel.uvprojx` in Keil.
- The application sources remain in `firmware/src/` and headers in `firmware/include/`; they are already referenced by the Keil project.
- CubeMX owns `Core/Inc`, `Core/Src`, `Drivers`, startup files, and HAL sources.
- Do **not** add CubeMX's generated `Core/Src/main.c` to the Keil target, because this repo provides the application `main()` in `firmware/src/main.c`.

If CubeMX regenerates `Core/Src/main.c`, preserve its generated `SystemClock_Config()` implementation by copying it into the marked section of `firmware/src/main.c`.

## 6. IOC settings that matter

Your `.ioc` should preserve at least:

- `Mcu.Name=STM32F427VGTx`
- `ProjectManager.ToolChain=MDK-ARM`
- `RCC.HSE_VALUE=8000000`
- PLL settings that produce `SYSCLKFreq_VALUE=168000000`
- `CAN1` enabled with RX FIFO0 interrupt
- `USART3` enabled at `115200`, 8N1, with interrupt
- peripheral init files generated separately

Those settings are the narrow throat of the firmware: if they drift, the application still compiles, but the board will not behave like the design assumes.
