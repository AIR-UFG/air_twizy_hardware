#!/bin/bash
# Entrypoint do cliente (dashboard). Sourceia ROS 2 + overlay com sd_msgs
# antes de rodar o `command` do docker-compose.
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"
source /root/ros2_ws/install/setup.bash

exec "$@"
