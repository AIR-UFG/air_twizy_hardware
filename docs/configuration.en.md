# Configuration Reference

All environment variables are defined in `.env` (copy from `env.exemple`). The root `docker-compose.yml` reads this file automatically.

## Shared (ROS2 / DDS / X11)

| Variable | Description | Default |
|----------|-------------|---------|
| `DISPLAY` | X11 display for graphical windows | `:0` |
| `QT_X11_NO_MITSHM` | Fix for Qt inside Docker | `1` |
| `ROS_DOMAIN_ID` | ROS2 DDS domain ID — must match across all machines | `42` |

## Camera (Lucid Vision)

| Variable | Description | Default |
|----------|-------------|---------|
| `CAMERA_IMAGE_NAME` | Docker image tag | `air-twizy-camera:latest` |
| `CAMERA_CONTAINER_NAME` | Container name | `air_twizy_camera` |
| `CAMERA_RMW_IMPLEMENTATION` | ROS2 middleware | `rmw_fastrtps_cpp` |
| `CAMERA_FASTRTPS_DEFAULT_PROFILES_FILE` | Path to FastDDS XML profile inside container | `/arena_camera_ros2/config/fastdds_subscriber.xml` |
| `CAMERA_SERIAL` | Lucid camera serial number | _(empty — uses first found)_ |
| `CAMERA_TOPIC` | ROS2 image topic name | `/camera/image_raw` |

## LiDAR (Ouster)

| Variable | Description | Default |
|----------|-------------|---------|
| `OUSTER_ROS_DISTRO` | ROS2 distro used in build arg | `humble` |
| `OUSTER_RMW_IMPLEMENTATION` | ROS2 middleware | `rmw_fastrtps_cpp` |
| `LIDAR_IMAGE_NAME` | Docker image tag | `air-twizy-lidar:latest` |
| `LIDAR_CONTAINER_NAME` | Container name | `air_twizy_lidar` |

!!! note "Ouster launch parameters"
    Ouster launch parameters (`sensor_hostname`, `udp_dest`, etc.) are not in `.env` — pass them directly to `ros2 launch` inside the container.

## Vehicle (Twizy)

| Variable | Description | Default |
|----------|-------------|---------|
| `CARRO_IMAGE_NAME` | Docker image tag | `air-twizy-car:latest` |
| `CARRO_CONTAINER_NAME` | Container name | `air_twizy_car` |
| `TWIZY_GPU` | Enable GPU for point cloud processing | `false` |
| `TWIZY_LIDAR` | Launch LiDAR integration inside vehicle stack | `false` |
| `TWIZY_INTERFACE` | Launch CAN vehicle interface | `true` |
| `TWIZY_CAN_PORT` | Host CAN interface (`can0`, `vcan0`, …) | `can0` |
| `NVIDIA_RUNTIME` | Docker runtime (`runc` or `nvidia`) | `runc` |
| `TWIZY_HOST_FOLDER_PATH` | ROS2 source packages path on host | `./workspace/twizy/ros_packages` |
| `TWIZY_SHARED_FOLDER` | Shared folder for bags and outputs | `./workspace/twizy/shared_folder` |
| `TWIZY_UTILS_PATH` | Utils scripts path on host | `./workspace/twizy/utils` |
| `TWIZY_XAUTHORITY` | X11 authority file for GPU containers | `/tmp/.docker.xauth` |

## FastDDS profile generation

The camera FastDDS profile must be regenerated whenever the streaming interface changes:

```bash
# Publisher side (camera machine)
./workspace/camera-lucid/config/setup_fastdds.sh publisher <interface>

# Subscriber side (receiver machine)
./workspace/camera-lucid/config/setup_fastdds.sh subscriber <interface>
```

This creates `fastdds_publisher.xml` or `fastdds_subscriber.xml` in the config directory.
