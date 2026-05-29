#!/bin/bash
# Entrypoint editável (montado no container) para o serviço `ouster_lidar`.
# Faz o source do ROS 2 e do overlay do workspace do ouster antes de executar
# o `command` definido no docker-compose.yml (ex.: ros2 launch ouster_ros ...).
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"

if [ -f /var/lib/build/install/setup.bash ]; then
    source /var/lib/build/install/setup.bash
fi

exec "$@"