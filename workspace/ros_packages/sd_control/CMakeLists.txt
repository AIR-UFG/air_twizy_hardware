cmake_minimum_required(VERSION 3.8)
project(sd_control)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2 REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sd_msgs REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

include_directories(
  include
  ${GAZEBO_INCLUDE_DIRS}
  ${rclcpp_INCLUDE_DIRS}
  ${tf2_INCLUDE_DIRS}
  ${nav_msgs_INCLUDE_DIRS}
  ${sd_msgs_INCLUDE_DIRS}
  ${gazebo_ros_INCLUDE_DIRS}
  ${geometry_msgs_INCLUDE_DIRS}
  ${sensor_msgs_INCLUDE_DIRS}
)

add_library(SdControlPlugin SHARED src/sd_control_plugin.cpp)
ament_target_dependencies(SdControlPlugin
  rclcpp
  gazebo_ros
  tf2
  nav_msgs
  sd_msgs
  geometry_msgs
  sensor_msgs
)
target_link_libraries(SdControlPlugin ${GAZEBO_LIBRARIES})

add_executable(sd_teleop_joy src/sd_teleop_joy.cpp src/sd_teleop_joy_node.cpp)
ament_target_dependencies(sd_teleop_joy
  rclcpp
  tf2
  nav_msgs
  sd_msgs
  geometry_msgs
  sensor_msgs
)

install(TARGETS SdControlPlugin sd_teleop_joy
  ARCHIVE DESTINATION lib/${PROJECT_NAME}
  LIBRARY DESTINATION lib/${PROJECT_NAME}
  RUNTIME DESTINATION bin/${PROJECT_NAME}
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  FILES_MATCHING PATTERN "*.launch" PATTERN "*.launch.py" PATTERN "*.machine" PATTERN "*.yaml" PATTERN "*.urdf"
)

install(PROGRAMS
  src/sd_teleop_keyboard.py
  src/sd_teleop_ps4.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
