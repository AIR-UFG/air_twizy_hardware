# Multi-machine Streaming

Stream camera images from the camera machine to a remote receiver over LAN or VPN.

## Why FastDDS profiles are needed

When a machine has multiple network interfaces (e.g., GigE camera port + WiFi), FastDDS advertises all interface IPs as data locators. The remote subscriber may then try to send ACKs to the GigE camera IP (169.254.x.x), which is not reachable from the remote side.

FastDDS unicast profiles restrict which IP is advertised. The publisher profile also includes the loopback address (`127.0.0.1`) so that co-located processes on the same machine (e.g., the compression relay) communicate at full speed.

## Bandwidth comparison

| Method | Resolution | Rate | Bandwidth | Notes |
|--------|-----------|------|-----------|-------|
| RAW throttled | 1024×768 | 15 FPS | ~12 Mbps | Low resolution only |
| JPEG compressed q=80 | 2048×1536 | 33 FPS | ~35–45 Mbps | Full res at full rate (WiFi OK) |
| RAW full | 2048×1536 | 33 FPS | ~825 Mbps | Requires 1 GbE link |

JPEG compression is the recommended approach for streaming.

## Setup

### Camera machine (publisher)

```bash
# Generate FastDDS profile for the streaming interface
./workspace/camera-lucid/config/setup_fastdds.sh publisher <streaming-interface>
# Example: ./config/setup_fastdds.sh publisher wlan0

# Start camera node at full FPS
./workspace/camera-lucid/scripts/start_camera.sh <serial> /camera/image_raw bayer_rggb8 "" "" 0 25000 33.0

# Start compression relay (separate terminal or background)
bash ./workspace/camera-lucid/notebook_setup/compress_stream.sh /camera/image_raw
```

### Receiver machine (Docker)

```bash
# Generate FastDDS profile for the receiving interface
./workspace/camera-lucid/config/setup_fastdds.sh subscriber <receiving-interface>
# Example: ./config/setup_fastdds.sh subscriber eth0

# Allow firewall traffic (if needed)
sudo bash ./workspace/camera-lucid/notebook_setup/setup_firewall_receiver.sh 192.168.X.0/24

xhost +local:docker
docker compose up -d camera
docker compose exec camera bash

# Inside container
source /opt/ros/humble/setup.bash
python3 /arena_camera_ros2/notebook_setup/stream_viewer.py \
    --topic /camera/image_raw --compressed
```

## Streaming over VPN (NetBird / WireGuard)

The Twizy project uses **NetBird** as its VPN — see [NetBird Setup](../networking/netbird.md). Multicast discovery does not work over any VPN tunnel. Use the [FastDDS Discovery Server](../networking/discovery-server.md) (recommended) or add `initialPeersList` manually with the remote peer's VPN IP:

```xml
<!-- Add inside <rtps> in fastdds_publisher.xml -->
<initialPeersList>
  <locator>
    <udpv4>
      <address>10.X.X.X</address>  <!-- remote peer VPN IP -->
      <port>11811</port>
    </udpv4>
  </locator>
</initialPeersList>
```

## Troubleshooting

**Topic visible but 0 frames received:**

- Most common cause: FastDDS advertising the wrong interface IP
- Run `setup_fastdds.sh` on both machines with the correct interface
- Confirm with `tcpdump -i any udp port 7400` that packets are on the right interface
- The subscriber FastDDS profile must use the IP where packets physically arrive (check with `tcpdump` — may differ from the default route interface)

**Fedora Kinoite / Silverblue receiver (Toolbox):**

See the [notebook_setup README](https://github.com/AIR-UFG/air_twizy_hardware/tree/main/workspace/camera-lucid/notebook_setup) for the full Toolbox-based setup procedure.
