# LiDAR — Ouster

ROS2 driver for Ouster OS-series LiDAR sensors, packaged as a Docker container.

Source: [ouster-lidar/ouster-ros](https://github.com/ouster-lidar/ouster-ros) (included as a submodule).

## Requirements

- Ouster OS-series sensor connected via Ethernet
- Sensor hostname or IP address known (use `avahi-resolve -n <hostname>.local` for link-local)

## Quick Start

```bash
docker compose up -d lidar
docker compose exec lidar bash

# Inside container — start the driver
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ouster_ros sensor.composite.launch.xml \
    sensor_hostname:=<SENSOR_IP_OR_HOSTNAME>
```

## Published Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/ouster/points` | `sensor_msgs/PointCloud2` | 3D point cloud |
| `/ouster/imu` | `sensor_msgs/Imu` | IMU data |
| `/ouster/scan` | `sensor_msgs/LaserScan` | 2D scan slice |
| `/ouster/image` | `sensor_msgs/Image` | Range/intensity image |

## Key Parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| `sensor_hostname` | Sensor IP or hostname | `os-XXXX.local` or IP |
| `lidar_mode` | Resolution and scan rate | `512x10`, `1024x10`, `1024x20`, `2048x10` |
| `point_type` | Point cloud field format | `original`, `xyz`, `xyzi`, `xyzir` |
| `proc_mask` | Enable/disable message types | `IMU\|PCL\|SCAN\|IMG\|RAW\|TLM` |
| `use_system_default_qos` | Use default QoS (needed for rosbag) | `false` (default) |
| `min_range` / `max_range` | Range filter in meters | `0.0` / `1000.0` |

Full parameter reference: `workspace/ouster-ros/ouster-ros/config/driver_params.yaml`

## Recording a Bag

```bash
# Inside the lidar container
ros2 bag record /ouster/points /ouster/imu -s mcap -o ouster_bag
```

## Replay from bag or PCAP

```bash
# From ROS2 bag
ros2 launch ouster_ros replay.composite.launch.xml bag_file:=/path/to/bag

# From PCAP
ros2 launch ouster_ros replay_pcap.launch.xml \
    pcap_file:=/path/to/file.pcap \
    metadata:=/path/to/metadata.json
```

## Visualization

```bash
# Launch with RViz
ros2 launch ouster_ros sensor.composite.launch.xml \
    sensor_hostname:=<IP> viz:=true
```

## Troubleshooting

**No data received:**

- Verify the sensor is reachable: `ping <sensor_hostname>`
- Check `udp_dest` — if the host has multiple interfaces, specify the interface IP where UDP packets should arrive
- Ensure no firewall is blocking UDP ports used by the sensor

**Wrong timestamps:**

- Set `timestamp_mode` to `TIME_FROM_ROS_TIME` if the sensor has no GPS sync
