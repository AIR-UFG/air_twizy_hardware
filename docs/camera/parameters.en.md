# Camera Node Parameters

All parameters are **startup-only** — the node must be restarted to apply any change.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `serial` | int | Camera serial number | first available |
| `topic` | string | ROS2 topic name | `/arena_camera_node/images` |
| `pixelformat` | string | `bayer_rggb8`, `rgb8`, `bgr8`, `mono8`, … | `rgb8` |
| `width` | int | Image width in pixels | camera maximum |
| `height` | int | Image height in pixels | camera maximum |
| `gain` | float | Sensor gain in dB | `0.0` |
| `exposure_time` | float | Exposure in microseconds | camera default |
| `frame_rate` | float | Target acquisition frame rate (FPS) | camera default |
| `trigger_mode` | bool | `true` = triggered, `false` = continuous | `false` |
| `qos_reliability` | string | `reliable` or `best_effort` | `reliable` |

## frame_rate and exposure_time interaction

The actual frame rate is limited by whichever is lower: the `frame_rate` setting or `1 / exposure_time`.

For maximum FPS at a given rate, keep exposure short enough to allow it.

**Example — 33 FPS at full resolution:**
```bash
ros2 run arena_camera_node start --ros-args \
    -p serial:=<YOUR_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8 \
    -p frame_rate:=33.0 \
    -p exposure_time:=25000
```

25 ms exposure → allows up to 40 FPS, so the 33 FPS `frame_rate` cap takes effect.

## Using the launch script

```bash
# Inside the container
./scripts/start_camera.sh <serial> <topic> <pixelformat> <width> <height> <gain> <exposure> <fps>

# Example
./scripts/start_camera.sh 12345678 /camera/image_raw bayer_rggb8 "" "" 0 25000 33.0
```

Empty `""` arguments use the camera's maximum resolution.

## Multiple cameras

Scale with a YAML config:

```bash
cp workspace/camera-lucid/config/cameras_example.yaml workspace/camera-lucid/config/cameras.yaml
# edit cameras.yaml with serial numbers and topic names

ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py \
    config_file:=/arena_camera_ros2/config/cameras.yaml
```

!!! tip "Production deployments"
    For many cameras, use a gigabit switch with Jumbo Frame support and configure static IPs on each camera.
