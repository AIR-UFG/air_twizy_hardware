# Vehicle — AIR Twizy

ROS2-based vehicle stack for the AIR-UFG team's StreetDrone Twizy. This workspace covers both simulation (Gazebo) and real-world operation via CAN bus.

Source: [AIR-UFG/air_twizy_simulation](https://github.com/AIR-UFG/air_twizy_simulation) (included as a submodule at `workspace/twizy`).

## Workspace Structure

```
workspace/twizy/
├── docker/
│   ├── docker-compose.yml        # Standalone vehicle compose
│   └── Dockerfile
├── ros_packages/
│   ├── vehicle_interface_packages/
│   │   ├── ros2_socketcan/       # CAN bus ROS2 interface
│   │   └── SD-VehicleInterface/  # StreetDrone XCU integration
│   └── vehicle_simulation_packages/
│       ├── air_description/      # URDF/mesh descriptions
│       ├── air_sim/              # Gazebo world and plugins
│       └── vehicle_control_plugin/
└── utils/
    ├── run.sh                    # Container launcher with env flags
    ├── build_docker.sh
    ├── bash_container.sh         # Shell into running container
    └── record_bag.sh
```

## Quick Start

```bash
docker compose up -d carro
docker compose exec carro bash
```

### Simulation (Gazebo)

```bash
# Inside the container
./utils/run.sh GPU=false RVIZ=false
```

Once Gazebo opens, press **Play**. Then in another terminal:

```bash
docker compose exec carro bash

# Keyboard control
ros2 run vehicle_control sd_teleop_keyboard_control.py
```

Controls:

| Key | Action |
|-----|--------|
| W | Increase velocity |
| S | Decrease velocity |
| A | Turn left |
| D | Turn right |
| X | Stop |

### Real vehicle

```bash
# Bring up CAN interface on host
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Start container with CAN and vehicle interface enabled
TWIZY_INTERFACE=true TWIZY_CAN_PORT=can0 docker compose up -d carro
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TWIZY_GPU` | Enable GPU for point cloud processing | `false` |
| `TWIZY_LIDAR` | Launch LiDAR integration | `false` |
| `TWIZY_INTERFACE` | Launch vehicle interface (CAN) | `true` |
| `TWIZY_CAN_PORT` | Host CAN interface name | `can0` |
| `TWIZY_GPU` / `NVIDIA_RUNTIME` | NVIDIA runtime for GPU containers | `runc` |

## Recording

```bash
# Inside the container
# Record specific topics
./utils/record_bag.sh my_run specific /velodyne_points /camera/image_raw

# Record all topics
./utils/record_bag.sh my_run all
```

Bags are stored in `workspace/twizy/shared_folder/` (volume-mounted from host).

---

## Vehicle Interface Packages

The `vehicle_interface_packages` workspace provides ROS2-based communication with the StreetDrone Twizy hardware via CAN bus.

### ros2_socketcan

Handles CAN bus communication in ROS2 using the SocketCAN protocol.

- Implements ROS2 nodes for CAN bus interfacing
- Publishes/subscribes `can_msgs/Frame` messages
- Supports standard SocketCAN kernel driver (`can0`, `vcan0`, etc.)

```bash
ros2 launch ros2_socketcan socket_can_bridge.launch.xml interface:=can0
```

### SD-VehicleInterface

Integrates the StreetDrone Xenos Control Unit (XCU) with the ROS2 navigation stack.

- Translates `ackermann_msgs/AckermannDriveStamped` commands to CAN frames
- Publishes vehicle speed, steering angle, and status

**Subscribed topics:**
| Topic | Type | Description |
|-------|------|-------------|
| `/sd_control` | `ackermann_msgs/AckermannDriveStamped` | Drive commands |

**Published topics:**
| Topic | Type | Description |
|-------|------|-------------|
| `/sd_status` | custom | Vehicle state (speed, steering, mode) |

### CAN Bus Setup

```bash
# Standard CAN (500 kbps — StreetDrone default)
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Verify
ip link show can0
candump can0  # should show CAN frames from the XCU
```

---

## Vehicle Operation — Real Example

### 1 — SSH into the vehicle

```bash
ssh air@twizy
# password: (ask team)
```

`twizy` resolves to `100.122.121.134` via NetBird VPN. **Both machines must have NetBird connected** before this works (`netbird status` on each).

!!! note "First connection"
    On the first SSH from a new machine, you will see a key fingerprint prompt:
    ```
    The authenticity of host 'twizy (100.122.121.134)' can't be established.
    ED25519 key fingerprint is SHA256:6KA7LU04JZoQ+1IiHqn3uDhkX+sSFLTbj2AMHe+xGgY.
    Are you sure you want to continue connecting (yes/no/[fingerprint])?
    ```
    Type `yes` (not just `y` — SSH rejects the abbreviated answer). The key is then saved permanently.

---

### 2 — Navigate to the repository

The repository lives at `~/tmp_mota/air_twizy_simulation/` on the vehicle. There are similar directories for other team members (`tmp_simoes/`, `tmp_victor/`) — use `tmp_mota/`.

```bash
cd ~/tmp_mota/air_twizy_simulation
```

The repo structure at this path:

```
air_twizy_simulation/
├── docker/
│   └── docker-compose.yml
├── ros_packages/
├── shared_folder/
└── utils/
    ├── run.sh              ← use this to start/restart containers
    ├── bash_container.sh   ← use this to enter the container
    ├── record_bag.sh
    ├── direct_control/
    │   └── direct_teleop.py
    └── ...
```

---

### 3 — Start the containers

```bash
# Must be run from air_twizy_simulation/ root
./utils/run.sh
```

Expected output:

```
Running without NVIDIA GPU support.
[+] Running 2/2
 ✔ Container fastdds_server     Started
 ✔ Container air_car_container  Started
```

This starts two containers:
- `air_car_container` — main vehicle container (ROS2 + SD-VehicleInterface)
- `fastdds_server` — FastDDS Discovery Server on port 11811

!!! warning "Do NOT use `docker compose up` directly"
    Running `docker compose up` from the repo root will fail with `no configuration file provided: not found`. The compose file is at `docker/docker-compose.yml` and requires environment variables that only `run.sh` sets correctly. Always use `./utils/run.sh`.

!!! warning "Run from the repo root, not from `utils/`"
    `run.sh` references `docker/docker-compose.yml` relative to its working directory. If you are inside `utils/` when you run it, the path resolution fails. Always `cd ~/tmp_mota/air_twizy_simulation` first.

!!! note "Non-blocking warnings from run.sh"
    These appear every time and can be ignored:
    ```
    xhost: unable to open display ""             ← no screen over SSH, harmless
    touch: /tmp/.docker.xauth: Permission denied ← same reason, harmless
    cp: cyclonedds_vehicle.xml.template: No such file or directory ← template missing, does not affect operation
    ```

---

### 4 — Enter the container

```bash
./utils/bash_container.sh
# Opening bash in the container...
# root@twizy:~#
```

This opens a bash shell inside `air_car_container` as root.

!!! warning "Source ROS2 before running any `ros2` command"
    The container's interactive bash shell does **not** automatically source ROS2. You must run this every time you open a new shell inside the container:
    ```bash
    source /opt/ros/humble/setup.bash
    ```
    Without it, `ros2` commands will not be found and Python scripts that import `rclpy` will fail silently or with import errors.

    The workspace packages (sd_vehicle_interface, ros2_socketcan, etc.) are already sourced via the container entrypoint — only the base ROS2 install needs this manual `source`.

---

### 5 — Launch the vehicle interface

```bash
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

This starts three ROS2 nodes:
- `sd_vehicle_interface_node` — translates ROS2 commands to CAN frames
- `socket_can_receiver_node_exe` — reads CAN frames from the bus
- `socket_can_sender_node_exe` — writes CAN frames to the bus

**The launch is working correctly when you see:**

```
[socket_can_receiver_node_exe-2] interface: can2
[socket_can_receiver_node_exe-2] applied filters: 0:0
```

The line `applied filters: 0:0` confirms the CAN socket is open and the XCU is sending frames. If this line does not appear within ~2 seconds of startup, the wrong CAN port is selected.

---

### CAN interface — which port to use

The StreetDrone XCU is physically connected to **`can2`** on this vehicle. The default `CAN_PORT=can2` inside the container is already correct.

| Interface | What happens | Meaning |
|-----------|-------------|---------|
| `can2` | `applied filters: 0:0` — no errors | **Correct** — XCU is on this bus |
| `can0` | `applied filters: 0:0` — but no XCU data flows | Interface is UP but XCU not connected here |
| `can1` | `applied filters: 0:0` then immediately: `Error sending: No buffer space available` + `Error receiving: CAN Receive Timeout` | Bus is UP but no node responds — buffer fills immediately |

!!! warning "`can0` and `can1` do not cause an immediate crash"
    Both interfaces start without error and show `applied filters: 0:0`. The problem only becomes apparent when you try to send a command — with `can1` you see errors immediately; with `can0` the interface appears healthy but the XCU never receives or sends data. Always verify `applied filters: 0:0` appeared **and** that no WARN lines follow.

If for any reason `CAN_PORT` was changed, reset it:

```bash
export CAN_PORT=can2
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

---

### Environment variables inside the container

Run `env` inside the container to verify the full environment. The values confirmed in production:

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

---

### 6 — Keyboard teleoperation (alternative to Xbox controller)

Open a **second terminal** on the vehicle (new SSH session or `tmux` pane) and enter the container again:

```bash
./utils/bash_container.sh
```

Then inside the container:

```bash
source /opt/ros/humble/setup.bash
python3 utils/direct_control/direct_teleop.py
```

Expected output:

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

The script publishes `sd_msgs/DirectControl` to `/direct_control_cmd` in real time.

**Steering behavior:**
- Each keypress increments or decrements the steering by **5 units**
- The value accumulates while the key is held: one press of `a` → -5, two presses → -10, etc.
- Maximum range: **-55 to +55** (the script clamps at this limit)
- Releasing the key does not center the steering — you must press the opposite direction or `x`

**Example observed values during a test session:**
```
Steering Value: -5.0    ← one 'd' press
Steering Value: -5.0
Steering Value: 5.0     ← switched to 'a'
Steering Value: 10.0
Steering Value: -55.0   ← held 'a' repeatedly until clamp
Steering Value: 0.0     ← returned to center
```

!!! warning "This terminal must be separate from the vehicle interface terminal"
    `direct_teleop.py` only publishes commands. The `sd_vehicle_interface` node (step 5) must be running in the other terminal to actually send those commands over CAN to the XCU.

---

### 7 — Stopping the containers

**Do NOT use `docker compose down`** — it requires the same environment variables that `run.sh` sets, and will fail with variable-not-set warnings if called from a plain shell:

```
WARN: The "CAN_PORT" variable is not set. Defaulting to a blank string.
invalid spec: ::rw: empty section between colons
```

Use `docker stop` by container name instead:

```bash
docker stop air_car_container fastdds_server
```

Verify they are stopped:

```bash
docker ps   # should be empty
```

To restart: run `./utils/run.sh` again from the repo root — it stops any existing containers and recreates them.
