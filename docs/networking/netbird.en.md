# NetBird VPN Setup

NetBird creates an encrypted mesh VPN between all team devices. Each machine gets a stable hostname and IP on the NetBird network regardless of its physical network or NAT.

## Why NetBird

- No static IP needed on the vehicle — the RUT950 has a dynamic 4G IP
- Peer-to-peer when possible (low latency), relay fallback when NAT blocks direct connection
- Works over 4G, WiFi, and any internet connection
- Free tier available for small teams (self-hosted or cloud)

## Installation (all machines)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sh
```

## Authentication and connection

```bash
# Generate an authentication token in the NetBird dashboard (cloud or self-hosted)
# then connect:
sudo netbird up --setup-key <generated_token>
```

## Verification

```bash
# List connected peers and their status
netbird status

# Both the vehicle and the operator machine should appear as "Connected"
# Example output:
# Peers:
#  twizy-pc                Connected, IP: 100.X.X.1
#  operator-laptop         Connected, IP: 100.X.X.2

# Test reachability
ping <vehicle_netbird_hostname>
```

## Network considerations for ROS2

The ROS2 Docker containers must use `network_mode: host` so that ROS2 traffic is routed through the NetBird interface (`wt0`) rather than being isolated inside Docker's bridge network.

```yaml
# docker-compose.yml excerpt
services:
  carro:
    network_mode: host   # required — routes ROS2 over NetBird wt0
```

!!! warning "Camera GigE interface conflict"
    The FastDDS Discovery Server must be configured to listen only on the NetBird interface (`wt0`), **not** on the GigE camera interface (`169.254.x.x`). Running the server on all interfaces caused a conflict that prevented the camera from connecting. See [Discovery Server](discovery-server.md) for the correct configuration.

## Checking the NetBird interface

```bash
ip addr show wt0
# Should show a 100.x.x.x or similar address assigned by NetBird
```
