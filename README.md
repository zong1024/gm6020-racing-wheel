# GM6020 Racing Wheel / 赛车方向盘

一个参考项目，用于围绕 DJI GM6020 和 Robomaster C Board (STM32F427) 构建带力驱动的方向盘：包含 STM32 HAL 固件、Python 串口桥接、虚拟手柄输出，以及基于浏览器的调参仪表板。

## 仓库结构

```text
firmware/  STM32 应用层 C 代码和 CMake 目标
pc/        Python 串口桥接、WebUI 和配置
docs/      接线和配置说明
```

## 已实现功能

- 通过 `0x1FF` 输出 GM6020 CAN 指令，并从 `0x205` 解析反馈
- 多圈编码器跟踪、RPM 和转矩电流遥测
- 用于方向盘角度控制的 1 kHz PID 位置环
- 用于实时目标角度和 PID 调参的 UART 指令通道
- 启动时逻辑居中，并通过软件将行程限制在 `±360°`
- Flask WebUI，支持实时遥测、动画方向盘、PID 滑块、居中/校准控制，以及配置保存/加载
- 通过 `vgamepad` 输出虚拟 Xbox 手柄方向控制

## 硬件

- DJI GM6020 电机
- Robomaster C Board / STM32F427
- 适用于该电机的 24 V 电源
- 从开发板连接到 PC 的 USB 线缆
- 电机与开发板之间的 CAN 接线

精确接线示意图见 `docs/wiring.md`。

## 快速开始

### 固件

本仓库有意将固件保留为可移植的应用层，而不是提交某一个特定的 CubeMX 生成板级工程。请先生成 Robomaster C Board 支持工程，然后集成 `firmware/` 下的源码。代码要求：

- `CAN1` 用于 GM6020 总线
- `USART3` 使用 `115200 8N1`
- STM32 HAL 符号，例如 `hcan1`、`huart3`、`MX_CAN1_Init` 和 `MX_USART3_UART_Init`

详细步骤见 `docs/setup.md`。

### PC 应用

```bash
cd pc
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
# then open http://127.0.0.1:5000 in your browser
```

编辑 `pc/config.json` 以配置 COM 端口、角度范围、死区和初始 PID 数值。


## WebUI

PC 应用现在是一个由 Flask-SocketIO 提供服务的单页深色仪表板。它以 20 Hz 向浏览器推送遥测数据，并通过 WebSocket 将 PID 更新、目标角度变化、居中、校准和配置操作回传，无需刷新页面。

### 截图

当方向盘连接并运行后，在这里添加截图：

```text
docs/screenshots/dashboard.png
docs/screenshots/pid-tuning.png
```

## 控制模型

方向盘使用一个很小的串口协议：

```text
A,30.0          # set target angle to +30 degrees
PID,120,0,2.5   # update Kp/Ki/Kd
CENTER          # capture current position as logical zero
```

开发板回传的遥测格式如下：

```text
T,current_angle,target_angle,rpm,torque_current
```

WebUI 会将测得的方向盘角度转换为虚拟 Xbox 控制器的左 X 轴，因此赛车游戏可以像绑定普通转向设备一样绑定它。

## 安全说明

- 开始前请先拆下方向盘轮缘，或让电机处于空载状态。
- 如果 PID 增益设置不当，或 CAN 帧格式错误，GM6020 可能会剧烈运动。
- 软件限位不能替代物理急停。
- 本项目在启动时使用*逻辑*中心点；若需要真正可重复的回零，请添加传感器或机械回零装置。

## 后续值得添加的功能

- 添加专用 e-stop 输入和锁存故障状态
- 根据游戏遥测添加力反馈转矩模式
- 在 flash 中添加非易失性校准存储
- 添加用于绝对回零的硬件中心传感器
