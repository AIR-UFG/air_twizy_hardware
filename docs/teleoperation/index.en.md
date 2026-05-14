# Remote Teleoperation

The Twizy supports remote teleoperation via an Xbox controller connected to an operator laptop anywhere with internet access. Communication happens through the [NetBird VPN](../networking/netbird.md) and a [FastDDS Discovery Server](../networking/discovery-server.md) on the vehicle.

## System Overview

```
REMOTE OPERATOR                          VEHICLE (Twizy)
─────────────────────────────────────────────────────────
Xbox Controller                          FastDDS Discovery Server
     │                                         │ (port 11811)
  joy_node                              Vehicle controller nodes
     │                                         │
direct_teleop ──── /direct_control_cmd ──► SD-VehicleInterface
                ◄── /sd_control ──────────────┘
        └─────────── VPN NETBIRD (mesh) ───────┘
```

**Command flow:**

1. Operator sends torque and steering setpoints via `/direct_control_cmd`
2. Vehicle PC subscribes, applies commands to the Twizy via CAN, and publishes current state to `/sd_control`
3. The Discovery Server on the vehicle converts multicast ROS2 traffic to unicast, enabling cross-VPN communication

## Requirements

| Component | Version | Role |
|-----------|---------|------|
| OS | Ubuntu 22.04 LTS | Base for ROS2 Humble |
| ROS2 Middleware | `rmw_fastrtps_cpp` | Required for Discovery Server |
| VPN | NetBird (latest) | Mesh P2P communication |
| Containerization | Docker 24.x+ | Environment isolation |

**Hardware:**
- Operator: laptop with USB or Bluetooth Xbox controller
- Vehicle: on-board PC connected to Twizy CAN bus
- Both sides need internet access for the VPN

## Operation Procedure

### On the vehicle

```bash
# 1. Verify NetBird is connected and note the IP
netbird status

# 2. Start the Discovery Server
docker compose up -d discovery-server

# 3. Start the vehicle control nodes (subscribes /direct_control_cmd, publishes /sd_control)
docker compose up -d carro
```

### On the operator machine

```bash
# 1. Verify NetBird connectivity
ping <vehicle_netbird_hostname>

# 2. Set environment variables
export ROS_DISCOVERY_SERVER=<vehicle_netbird_hostname>:11811
export ROS_SUPER_CLIENT=true
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# 3. Start the teleop stack
docker compose up -d

# 4. Verify topics are visible
ros2 topic list
# Should show /direct_control_cmd and /sd_control
```

## ROS2 Package Structure

```
ws/
├── teleop_joy_xbox/          # Teleoperation package
│   ├── config/
│   │   └── xbox_controller.yaml
│   ├── launch/
│   │   ├── xbox_teleop.launch.py      # Mode 1: Twist (cmd_vel)
│   │   └── direct_teleop.launch.py    # Mode 2: Direct Control
│   └── teleop_joy_xbox/
│       ├── xbox_teleop_node.py
│       └── direct_teleop.py
└── sd_msgs/                  # Custom messages
    └── msg/
        ├── DirectControl.msg
        └── SDControl.msg
```

## Control Modes

### Mode 1 — Standard Twist

```bash
ros2 launch teleop_joy_xbox xbox_teleop.launch.py
```

- Message type: `geometry_msgs/Twist`
- Topic: `/cmd_vel`
- Use: generic mobile robots

### Mode 2 — Direct Control (recommended for Twizy)

```bash
ros2 launch teleop_joy_xbox direct_teleop.launch.py
```

- Messages: `sd_msgs/DirectControl` (commands), `sd_msgs/SDControl` (feedback)
- Topics: `/direct_control_cmd` → `/sd_control`
- Use: direct torque and steering control of the vehicle

See [Xbox Controller](xbox-controller.md) for button mapping and custom messages.

## Docker Compose (operator side)

```yaml
services:
  discovery-server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: fastdds_server
    network_mode: "host"
    command: -i 0
    restart: unless-stopped

  teleop-client:
    build:
      context: .
      dockerfile: Dockerfile.client
    container_name: ros2_teleop_joy
    network_mode: "host"
    depends_on:
      - discovery-server
    environment:
      - ROS_DISCOVERY_SERVER=<VEHICLE_NETBIRD_IP>:11811
      - ROS_DOMAIN_ID=0
      - ROS_SUPER_CLIENT=true
      - RMW_IMPLEMENTATION=rmw_fastrtps_cpp
    volumes:
      - ./ws:/root/ros2_ws/src:rw
      - /dev/input:/dev/input:rw
      - /run/udev:/run/udev:ro
    devices:
      - /dev/input
    command: ros2 run joy joy_node --ros-args -r /joy:=joy_teleop_test
```

!!! important "network_mode: host is mandatory"
    Without `network_mode: host`, Docker routes traffic through its bridge network instead of the NetBird interface (`wt0`). The ROS2 nodes would never reach the Discovery Server on the vehicle.
