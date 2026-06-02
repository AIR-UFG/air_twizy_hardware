#!/bin/bash
# Entrypoint editável (montado em /root/entrypoint_twizy.sh) para o serviço `carro`.
# Faz o source do ROS 2 e do overlay do ros2_ws antes de executar o `command`
# definido no docker-compose.yml (ex.: ros2 launch ...).
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"
source /root/ros2_ws/install/setup.bash

exec "$@"