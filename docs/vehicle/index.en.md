# Vehicle — AIR Twizy

ROS2-based vehicle stack for the AIR-UFG team's StreetDrone Twizy. This workspace covers both simulation (Gazebo) and real-world operation via CAN bus.

Source: [AIR-UFG/air_twizy_simulation](https://github.com/AIR-UFG/air_twizy_simulation) (included as a submodule at `workspace/twizy`).

## Workspace Structure

```
workspace/twizy/
├── docker/
│   ├── docker-compose.yml        # Standalone vehicle compose
│   └── Dockerfile
├── ros_packages/
│   ├── vehicle_interface_packages/
│   │   ├── ros2_socketcan/       # CAN bus ROS2 interface
│   │   └── SD-VehicleInterface/  # StreetDrone XCU integration
│   └── vehicle_simulation_packages/
│       ├── air_description/      # URDF/mesh descriptions
│       ├── air_sim/              # Gazebo world and plugins
│       └── vehicle_control_plugin/
└── utils/
    ├── run.sh                    # Container launcher with env flags
    ├── build_docker.sh
    ├── bash_container.sh         # Shell into running container
    └── record_bag.sh
```

## Quick Start

```bash
docker compose up -d carro
docker compose exec carro bash
```

### Simulation (Gazebo)

```bash
# Inside the container
./utils/run.sh GPU=false RVIZ=false
```

Once Gazebo opens, press **Play**. Then in another terminal:

```bash
docker compose exec carro bash

# Keyboard control
ros2 run vehicle_control sd_teleop_keyboard_control.py
```

Controls:

| Key | Action |
|-----|--------|
| W | Increase velocity |
| S | Decrease velocity |
| A | Turn left |
| D | Turn right |
| X | Stop |

### Real vehicle

```bash
# Bring up CAN interface on host
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Start container with CAN and vehicle interface enabled
TWIZY_INTERFACE=true TWIZY_CAN_PORT=can0 docker compose up -d carro
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TWIZY_GPU` | Enable GPU for point cloud processing | `false` |
| `TWIZY_LIDAR` | Launch LiDAR integration | `false` |
| `TWIZY_INTERFACE` | Launch vehicle interface (CAN) | `true` |
| `TWIZY_CAN_PORT` | Host CAN interface name | `can0` |
| `TWIZY_GPU` / `NVIDIA_RUNTIME` | NVIDIA runtime for GPU containers | `runc` |

## Recording

```bash
# Inside the container
# Record specific topics
./utils/record_bag.sh my_run specific /velodyne_points /camera/image_raw

# Record all topics
./utils/record_bag.sh my_run all
```

Bags are stored in `workspace/twizy/shared_folder/` (volume-mounted from host).
