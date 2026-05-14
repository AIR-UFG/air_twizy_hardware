# Getting Started

## Prerequisites

- **Docker** and **Docker Compose** v2+
- **Git** with submodule support
- Ubuntu 22.04 or later (recommended)
- For camera: Lucid Vision Triton camera with GigE Ethernet
- For LiDAR: Ouster OS-series sensor on Ethernet
- For vehicle: CAN interface (`can0`) wired to the StreetDrone Twizy XCU

## 1 — Clone the repository

```bash
git clone https://github.com/AIR-UFG/air_twizy_hardware.git
cd air_twizy_hardware
git submodule update --init --recursive
```

!!! tip "ArenaSDK (camera only)"
    The Lucid camera submodule requires the ArenaSDK and arena_api files to be placed manually before building:

    - `ArenaSDK_Linux_x64.tar.gz` → `workspace/camera-lucid/resources/ArenaSDK/linux64/`
    - `arena_api-*.whl` → `workspace/camera-lucid/resources/arena_api/`

    Download both from the [Lucid downloads hub](https://thinklucid.com/downloads-hub/).

## 2 — Configure environment variables

```bash
cp env.exemple .env
```

Edit `.env` with your machine-specific values. At minimum:

| Variable | Description | Example |
|----------|-------------|---------|
| `CAMERA_SERIAL` | Lucid camera serial number | `12345678` |
| `ROS_DOMAIN_ID` | Shared ROS2 domain (must match all machines) | `42` |
| `TWIZY_CAN_PORT` | Host CAN interface name | `can0` |

See [Configuration](configuration.md) for the full variable reference.

## 3 — Build Docker images

```bash
# Build all three services
docker compose build

# Or build individually
docker compose build camera
docker compose build lidar
docker compose build carro
```

## 4 — Hardware setup

=== "Camera (GigE)"
    ```bash
    # Tune the GigE interface (MTU, receive buffers, ring)
    sudo ./workspace/camera-lucid/scripts/setup_network.sh <gige-interface>

    # Assign a link-local IP to the interface
    sudo ip addr add 169.254.1.1/16 dev <gige-interface>

    # Allow containers to open graphical windows
    xhost +local:docker
    ```

=== "LiDAR (Ouster)"
    Connect the Ouster sensor to the host via Ethernet. The sensor auto-assigns
    a link-local IP by default. Use `avahi-resolve -n <hostname>.local` or check
    your DHCP server to find its IP before launching.

=== "Vehicle (CAN)"
    Bring up the CAN interface before starting the container:
    ```bash
    sudo ip link set can0 type can bitrate 500000
    sudo ip link set can0 up
    ```

## 5 — Start the services

```bash
# Start everything
docker compose up -d

# Or start a specific service
docker compose up -d camera
docker compose up -d lidar
docker compose up -d carro
```

## 6 — Open an interactive shell

```bash
docker compose exec camera bash
docker compose exec lidar bash
docker compose exec carro bash
```

## Stopping services

```bash
docker compose down
```
