cmake_minimum_required(VERSION 3.8)
project(sd_control)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  FILES_MATCHING PATTERN "*.launch.py"
)

install(PROGRAMS
  src/sd_teleop_ps4.py
  src/sd_teleop_gui.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
