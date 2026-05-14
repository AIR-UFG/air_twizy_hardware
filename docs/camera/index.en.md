# Camera — Lucid Vision Triton

ROS2 Humble driver for Lucid Vision Triton cameras (GigE Vision), packaged as a Docker container. Supports single and multi-camera setups, JPEG-compressed streaming over LAN or VPN, bag recording, and video export.

Adapted from the [official Lucid Vision ROS2 driver](https://github.com/lucidvisionlabs/arena_camera_ros2) (originally for ROS2 Eloquent).

## Requirements

- Lucid Vision Triton camera connected via GigE (Ethernet)
- ArenaSDK and arena_api files placed in `resources/` (see [Getting Started](../getting-started.md))
- GigE interface configured with `scripts/setup_network.sh`

## Quick Start

```bash
# Configure GigE interface (run on host, not inside container)
sudo ./workspace/camera-lucid/scripts/setup_network.sh <gige-interface>
sudo ip addr add 169.254.1.1/16 dev <gige-interface>

xhost +local:docker
docker compose up -d camera
docker compose exec camera bash

# Inside container — verify camera is detected
python3 /arena_camera_ros2/scripts/list_cameras.py

# Start camera node
ros2 run arena_camera_node start --ros-args \
    -p serial:=<YOUR_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8
```

## Directory Structure

```
workspace/camera-lucid/
├── Dockerfile                      # ROS2 Humble + ArenaSDK image
├── docker-compose.yml              # Standalone camera compose
├── config/
│   ├── setup_fastdds.sh            # Generates FastDDS unicast profiles
│   ├── cameras_example.yaml        # Multi-camera config template
│   └── fastdds_*.xml               # FastDDS profiles
├── scripts/
│   ├── setup_network.sh            # GigE interface tuning (MTU, buffers, ring)
│   ├── list_cameras.py             # Detect connected cameras
│   ├── start_camera.sh             # Camera node launcher
│   ├── compress_bayer_stream.py    # JPEG compression relay
│   ├── focus_helper.py             # Live focus score for lens adjustment
│   ├── record_video.py             # Direct MP4 recording
│   ├── bag_to_video.py             # Convert ROS2 bag to MP4
│   └── convert_bag.py              # One-command bag-to-video wrapper
├── notebook_setup/                 # Receiver-side tools
├── launch/
│   ├── multi_camera.launch.py      # Launch multiple cameras from YAML
│   └── camera_streaming.launch.py  # Streaming-optimized launch
└── ros2_ws/src/
    └── arena_camera_node/          # C++ ROS2 node wrapping ArenaSDK
```

## Bayer RAW format

Triton cameras output BayerRG8 natively. Use `pixelformat:=bayer_rggb8` for zero-copy RAW data. When processing in OpenCV:

```python
# ROS2 bayer_rggb8 maps to OpenCV BayerBG (naming is inverted)
bgr = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)
```

## Troubleshooting

**Camera not detected:**

- Check the Ethernet cable and camera power
- Run `sudo ./scripts/setup_network.sh <interface>` on the host
- Verify the host IP is on the same subnet: `ip addr show`
- Try `ping <camera-ip>`

**Image is grey or out of focus:**

- Triton cameras ship without a lens — a C-mount lens must be installed separately
- Adjust focus: `python3 /arena_camera_ros2/scripts/focus_helper.py`

**No graphical window:**

- Run `xhost +local:docker` on the host before starting the container

**Compile error: `True not declared`:**

- Fixed in this repository (upstream driver had Python `True` in C++ code)
