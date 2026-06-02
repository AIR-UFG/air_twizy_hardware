#!/bin/bash
# Host-editable entrypoint (mounted at /root/entrypoint_twizy.sh) for the `car` service.
# Sources ROS 2 and the ros2_ws overlay before running the `command`
# from docker-compose.yml (e.g. ros2 launch ...).
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"
source /root/ros2_ws/install/setup.bash

exec "$@"
