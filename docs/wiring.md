# Wiring

```text
24 V PSU +  --------------------+---------------- GM6020 VIN+
24 V PSU -  --------------------+---------------- GM6020 GND
                                 |
                                 +---------------- Robomaster C GND

GM6020 CAN_H --------------------- Robomaster C Board CAN_H
GM6020 CAN_L --------------------- Robomaster C Board CAN_L

Robomaster C Board USB ------------ PC USB
```

Notes:
- Share ground between the 24 V supply, GM6020, and Robomaster C board.
- Keep CAN_H/CAN_L as a twisted pair.
- Add proper CAN termination if your bus topology requires it; for a two-end bus, the usual practice is 120 ohm at each physical end.
- Do not hot-plug the motor power connector while the system is energized.
