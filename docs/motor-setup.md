# GM6020 setup for use with a RoboMaster C Board

## Quick reference

| Item | Setting for this project | Notes |
| --- | --- | --- |
| Control path | **CAN** | The GM6020 auto-detects CAN vs PWM from the incoming signal; there is no separate “CAN mode” switch to set. |
| Motor ID | **1** | Set with the physical DIP switches, not in RoboMaster Assistant. ID 1 sends feedback on `0x205`, which matches this repo. |
| CAN bitrate | **1 Mbps** | Fixed by the GM6020 protocol. Use standard 11-bit CAN frames, data frames, DLC 8. |
| CAN command ID used by this repo | **`0x1FF`** | This is the GM6020 **voltage-control** command frame for motor IDs 1–4. |
| Current Ring switch | **OFF for this repo as written** | This firmware currently transmits `0x1FF`; if you turn Current Ring ON, you must also change the firmware to send current-control frames instead. |
| PWM mode | Irrelevant for CAN use | Leave PWM settings alone unless you also plan to drive the motor by PWM. |
| CAN termination | Enable only if the motor is at a physical bus end | DIP switch bit 4 controls the GM6020's built-in termination resistor. |
| Recommended firmware | **Latest available; at least `v1.0.11.2` if you need current mode** | `v1.0.11.2+` is required for the Assistant “Current Ring On/Off” feature. |

## Step-by-step setup

### 1. Connect the motor to RoboMaster Assistant

1. Power the GM6020 from a 24 V supply.
2. Connect the GM6020 to the PC through the motor's **PWM port** using a USB-to-serial adapter:
   - black = GND
   - grey = TX
   - white = PWM/RX
3. Open **RoboMaster Assistant** and confirm that the GM6020 is detected.

RoboMaster Assistant is used here for parameter inspection and firmware update. The GM6020 does **not** need a software-selected CAN mode before it can listen on CAN.

### 2. Update firmware first

1. Open **Firmware Update** in RoboMaster Assistant.
2. Install the latest GM6020 firmware offered by the tool.
3. If you intend to use **current-control mode**, make sure the motor firmware is at least **`v1.0.11.2`** and RoboMaster Assistant is **v2.7 or later**.

For this repository, updating is still sensible, but current-control mode is **not** what the checked-in firmware currently speaks.

### 3. Set the motor ID with the DIP switches

Set the first three DIP-switch bits to **ID 1**:

```text
Bit2 Bit1 Bit0 = 0 0 1
```

That gives:

| Motor ID | Feedback CAN ID | Command CAN ID family |
| --- | --- | --- |
| 1 | `0x205` | `0x1FF` for voltage mode / `0x1FE` for current mode |

Use a unique ID for every motor on the same CAN bus. If two motors share an ID, the GM6020 status LED reports an ID conflict.

Why ID 1 here: this repo expects feedback at `0x205` (`GM6020_CAN_RX_ID_BASE = 0x205`, motor index `0`).

### 4. Configure the settings that actually matter in RoboMaster Assistant

For **this repo as currently written**:

1. Leave **Current Ring On/Off = OFF**.
2. Do not worry about PWM speed/position settings; they apply to PWM control, not CAN control.
3. Save/apply the settings if the Assistant exposes an apply/write action.

The reason is subtle but important: this repo sends commands on `0x1FF`, which the GM6020 manual defines as the **voltage-control** CAN frame. If you enable **Current Ring**, the motor expects the **current-control** frame IDs instead (`0x1FE` / `0x2FE`). In that case, the firmware must be changed too; flipping only the Assistant setting can make the motor appear “dead” to otherwise-valid CAN traffic.

### 5. Set up the CAN bus on the RoboMaster C Board

Configure the C Board's CAN peripheral as follows:

| CAN parameter | Value |
| --- | --- |
| Bitrate | `1 Mbps` |
| Frame type | Standard CAN, 11-bit identifier |
| Frame format | Data frame |
| DLC | `8` bytes |

For one GM6020 at ID 1 in this repo:

- transmit commands on `0x1FF`
- listen for feedback on `0x205`

The GM6020 publishes feedback at **1 kHz**.

### 6. Set CAN termination correctly

Use DIP-switch bit 4 only for **bus termination**:

- enable it if the GM6020 is at one physical end of the CAN bus and needs to provide one of the two end resistors
- disable it if the motor is in the middle of the bus or another termination scheme is already in place

A healthy two-end CAN bus normally has one termination resistor at each physical end, not on every device.

## “Idle” vs “brake” mode

For CAN operation, there is no required RoboMaster Assistant setting called **idle**, **idol**, or **brake** mode that must be selected before the motor will answer CAN commands.

What matters is:

1. the motor has a valid DIP-switch ID,
2. the CAN bus is wired and timed correctly,
3. your command frame matches the motor's selected control interpretation:
   - `0x1FF` / `0x2FF` for voltage-control mode,
   - `0x1FE` / `0x2FE` for current-control mode after enabling **Current Ring**.

If you send zero command, the motor simply produces zero commanded output; that is not a separate “brake mode” configuration step in Assistant.

## Common pitfalls

- **Trying to set the CAN ID in Assistant.** The GM6020 CAN ID is set by the physical DIP switches.
- **Leaving the DIP switches at `000`.** The manual marks that motor ID as invalid.
- **Using the wrong feedback ID.** ID 1 reports on `0x205`, not `0x204`.
- **Turning Current Ring ON while still transmitting `0x1FF`.** This repo currently uses `0x1FF`, so leave Current Ring OFF unless you also update the firmware protocol.
- **Wrong CAN bitrate.** The GM6020 bus bitrate is `1 Mbps`.
- **Duplicate IDs on one bus.** The motor LED can warn about this, and traffic will collide logically even if wiring is fine.
- **Bad termination.** Too many or too few terminators can make a perfectly good firmware look broken.
- **Expecting PWM settings to affect CAN behavior.** PWM position/speed mode is separate from CAN control.
- **Forgetting power or common ground.** The CAN pair alone is not enough; the motor still needs 24 V power and the system should share ground as designed.

## Source notes

This guide is based on DJI's **GM6020 Brushless DC Motor User Guide v1.4 (2023.10)** and DJI's official **RoboMaster Assistant** product page. The repository-specific notes above were checked against the current firmware in this project, which uses `0x1FF` for transmit and `0x205` for motor-1 feedback.
