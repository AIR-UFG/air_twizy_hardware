# Recording

## Direct MP4 (recommended)

Records video directly from the camera topic without intermediate files:

```bash
python3 /arena_camera_ros2/scripts/record_video.py --output camera.mp4
# Press Ctrl+C to stop and finalize the file
```

## ROS2 Bag (lossless, for post-processing)

```bash
cd /arena_camera_ros2/bags
ros2 bag record /camera/image_raw -s mcap
```

The bag is stored in `workspace/camera-lucid/bags/` on the host (volume-mounted).

## Convert bag to MP4

```bash
# Using the one-command wrapper
python3 /arena_camera_ros2/scripts/convert_bag.py ./my_bag --output video.mp4

# Or the lower-level script
python3 /arena_camera_ros2/scripts/bag_to_video.py --bag ./my_bag --output video.mp4
```

## Record only compressed stream

If the compression relay is running, record the compressed topic for smaller files:

```bash
ros2 bag record /camera/image_raw/compressed -s mcap -o compressed_bag
```
