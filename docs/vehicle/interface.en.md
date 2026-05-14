# Vehicle Interface Packages

The `vehicle_interface_packages` workspace provides ROS2-based communication with the StreetDrone Twizy hardware via CAN bus.

## Packages

### ros2_socketcan

Handles CAN bus communication in ROS2 using the SocketCAN protocol.

- Implements ROS2 nodes for CAN bus interfacing
- Publishes/subscribes `can_msgs/Frame` messages
- Supports standard SocketCAN kernel driver (`can0`, `vcan0`, etc.)

**Launch:**
```bash
ros2 launch ros2_socketcan socket_can_bridge.launch.xml interface:=can0
```

### SD-VehicleInterface

Integrates the StreetDrone Xenos Control Unit (XCU) with the ROS2 navigation stack.

- Translates `ackermann_msgs/AckermannDriveStamped` commands to CAN frames
- Publishes vehicle speed, steering angle, and status
- Supports both simulation (Gazebo) and real vehicle

**Key subscribed topics:**
| Topic | Type | Description |
|-------|------|-------------|
| `/sd_control` | `ackermann_msgs/AckermannDriveStamped` | Drive commands |

**Key published topics:**
| Topic | Type | Description |
|-------|------|-------------|
| `/sd_status` | custom | Vehicle state (speed, steering, mode) |

## CAN Bus Setup

The host CAN interface must be configured before starting the container:

```bash
# Standard CAN (500 kbps — StreetDrone default)
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Verify
ip link show can0
candump can0  # should show CAN frames from the XCU
```

## Compatibility

These packages run in both simulation and real environments:

- **Simulation**: The `SD-VehicleInterface` reads commands and moves the Gazebo model via a vehicle control plugin
- **Real vehicle**: Commands are translated to CAN frames and sent to the XCU over `can0`
