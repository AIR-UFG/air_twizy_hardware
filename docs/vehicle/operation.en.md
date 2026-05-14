# Vehicle Operation — Real Example

This page documents a real operation session on the Twizy, including SSH access via NetBird, container startup, vehicle interface launch, and keyboard teleoperation.

## 1 — SSH access via NetBird

The vehicle PC (`twizy`) is reachable by hostname thanks to NetBird:

```bash
ssh air@twizy
# resolves to NetBird IP: 100.122.121.134
```

Verify NetBird is running on both machines before connecting (`netbird status`).

## 2 — Start the containers on the vehicle

```bash
# Navigate to the vehicle repo (adjust path per user workspace)
cd ~/tmp_mota/air_twizy_simulation

# Start both containers: air_car_container + fastdds_server
./utils/run.sh
```

Expected output:

```
Running without NVIDIA GPU support.
[+] Running 2/2
 ✔ Container fastdds_server     Started
 ✔ Container air_car_container  Started
```

!!! warning "Run from the repo root"
    `run.sh` must be called from the `air_twizy_simulation/` root, not from inside `utils/`. The script internally references `docker/docker-compose.yml`.

!!! note "Non-blocking warnings"
    - `xhost: unable to open display` — normal when connected via SSH without X forwarding. Containers start normally.
    - `cp: cyclonedds_vehicle.xml.template: No such file or directory` — template file missing, does not prevent operation.

## 3 — Enter the container

```bash
./utils/bash_container.sh
# Opening bash in the container...
# root@twizy:~#
```

## 4 — Launch the vehicle interface

```bash
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

Expected output when the correct CAN interface is active:

```
[socket_can_receiver_node_exe-2] interface: can2
[socket_can_receiver_node_exe-2] applied filters: 0:0
```

The `applied filters: 0:0` line confirms the CAN socket is open and receiving.

## CAN interface — important

The StreetDrone XCU is connected on **`can2`** on this vehicle. The `CAN_PORT` environment variable inside the container defaults to `can2`.

| Interface | Result |
|-----------|--------|
| `can0` | `socket_can_receiver` starts but dies immediately (exit -6) |
| `can1` | `Error sending CAN message: No buffer space available` + receive timeout |
| `can2` | Correct — `applied filters: 0:0`, no errors |

If the wrong port is active, override it before launching:

```bash
export CAN_PORT=can2
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy sd_gps_imu:=peak sd_speed_source:=vehicle_can_speed
```

## Environment variables (inside container)

Confirmed from a running container (`env`):

```
ROS_DOMAIN_ID=0
ROS_SUPER_CLIENT=true
ROS_DISCOVERY_SERVER=twizy:11811
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROS_LOCALHOST_ONLY=0
CAN_PORT=can2
INTERFACE=true
LIDAR=false
GPU=false
```

The `ROS_DISCOVERY_SERVER=twizy:11811` uses the NetBird hostname — the Discovery Server container (`fastdds_server`) is listening on port 11811.

## 5 — Keyboard teleoperation (alternative to Xbox controller)

For quick testing without an Xbox controller, use the keyboard teleop script directly inside the container:

```bash
# Inside the container
source /opt/ros/humble/setup.bash
python3 utils/direct_control/direct_teleop.py
```

```
Reading from the keyboard and Publishing to TwistStamped!
Uses "w, a, s, d, x" keys
---------------------------
Move forward:   'w'
Move backward:  's'
Turn left:      'a'
Turn right:     'd'
Stop:           'x'

CTRL-C to quit

Torque Setpoint: 0.0, Steering Value: 0.0
```

The script publishes `sd_msgs/DirectControl` to `/direct_control_cmd` in real time. Steering values increment in steps of 5 per keypress (e.g., holding `a` gives -5, -10, -15, …, -55).

!!! note
    This script requires the vehicle interface nodes to be running in a separate terminal (step 4) to actually move the vehicle. The teleop only publishes commands; the `sd_vehicle_interface` node is what sends them over CAN.

## Stopping

```bash
# Stop containers from outside:
docker stop air_car_container fastdds_server

# Or using run.sh (it stops and recreates):
./utils/run.sh
```
