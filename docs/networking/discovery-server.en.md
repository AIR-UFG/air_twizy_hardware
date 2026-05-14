# FastDDS Discovery Server

Standard ROS2 relies on multicast for node discovery, which does not work across VPN tunnels or between machines on different networks. The solution is a **centralized FastDDS Discovery Server** running on the vehicle, which all nodes (local and remote) register with via unicast.

## How it works

```mermaid
sequenceDiagram
    participant V as Vehicle PC
    participant DS as Discovery Server (port 11811)
    participant O as Remote Operator

    V->>DS: register nodes (local, via 127.0.0.1 or wt0)
    O->>DS: register nodes (via NetBird IP)
    DS-->>V: peer list
    DS-->>O: peer list
    V<-->>O: ROS2 topic exchange (unicast)
```

## Setup on the vehicle

### Dockerfile.server

```dockerfile
FROM ros:humble-ros-core
RUN apt-get update && apt-get install -y \
    ros-humble-rmw-fastrtps-cpp \
    fastdds-tools \
    && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["fastdds", "discovery"]
```

### docker-compose.yml (vehicle side)

```yaml
services:
  discovery-server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: fastdds_server
    network_mode: "host"        # must use host to reach NetBird wt0 interface
    command: -i 0               # discovery server ID 0
    restart: unless-stopped
```

Start it:

```bash
docker compose up -d discovery-server
```

Or without Docker:

```bash
source /opt/ros/humble/setup.bash
fastdds discovery -i 0
```

!!! warning "GigE camera conflict"
    Running the Discovery Server without binding it to a specific interface caused it to advertise on the camera's GigE interface (`169.254.x.x`), blocking camera connections. Using `network_mode: host` combined with the NetBird-only FastDDS profile resolves this.

## Environment variables

### Vehicle side

```bash
# No special discovery server env needed — it's the server itself
ROS_DOMAIN_ID=0
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

### Operator side

```bash
export ROS_DISCOVERY_SERVER=twizy:11811   # NetBird hostname of the vehicle
export ROS_SUPER_CLIENT=true              # disables multicast, forces Discovery Server usage
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

| Variable | Value | Description |
|----------|-------|-------------|
| `ROS_DISCOVERY_SERVER` | `twizy:11811` | NetBird hostname (or IP) of the vehicle running the server |
| `ROS_DOMAIN_ID` | `0` | Must be identical on all machines in the network |
| `ROS_SUPER_CLIENT` | `true` | Disables multicast, forces exclusive use of Discovery Server |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | Sets FastDDS as the ROS2 middleware |

## Verification

```bash
# On any machine with the env vars set:
ros2 topic list
# Should show topics from the vehicle
```
