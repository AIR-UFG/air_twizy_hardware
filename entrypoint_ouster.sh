#!/bin/bash
# Host-editable entrypoint (mounted in the container) for the `ouster_lidar` service.
# Sources ROS 2 and the Ouster workspace overlay before running the `command`
# from docker-compose.yml (e.g. ros2 launch ouster_ros ...).
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"

if [ -f /var/lib/build/install/setup.bash ]; then
    source /var/lib/build/install/setup.bash
fi

exec "$@"
