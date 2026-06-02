# air_twizy_hardware

Hardware stack for the AIR-UFG autonomous Twizy: **Lucid camera**, **Ouster LiDAR**, and **vehicle interface (CAN)** via Docker Compose and ROS 2 Humble.

Additional documentation (architecture, diagrams): [air_twizy_hardware_docs](https://ruigonc.github.io/air_twizy_hardware_docs/).

---

## Overview

| Compose service | Container (default) | Role |
|-----------------|---------------------|------|
| `discovery-server` | `discovery_server` | Fast DDS Discovery server (`fastdds discovery`) |
| `camera` | `air_twizy_camera` | Lucid Triton cameras (GigE) → `/camera_N/image_raw` topics |
| `ouster_lidar` | `ouster_lidar` | Ouster LiDAR (Ethernet) → ROS point cloud |
| `car` | `air_car_container` | `SD-VehicleInterface` + SocketCAN bridge |

All services use **`network_mode: host`**, **`privileged: true`** (where applicable), and the same **`ROS_DOMAIN_ID`**. The `car` service requires the CAN interface on the **host** to be up before or shortly after the container starts.

---

## Host prerequisites

- Ubuntu 22.04 (or compatible) with **Docker** and **Docker Compose v2** (`docker compose`)
- Git with submodules
- For GUI (RViz, etc.): X11 server on the host (`DISPLAY`, usually `:0`)
- Hardware:
  - **PEAK** adapter(s) (USB and/or PCIe) for CAN
  - Lucid camera(s) on GigE (if using `camera`)
  - Ouster on dedicated Ethernet (`enp11s0` on this machine) with static network configured (section 3)
- Useful host packages (CAN diagnostics):

```bash
sudo apt-get install -y can-utils iproute2
```

---

## 1. Clone and initialize submodules

```bash
git clone https://github.com/AIR-UFG/air_twizy_hardware.git
cd air_twizy_hardware
git submodule update --init --recursive
```

Submodules:

| Path | Contents |
|------|----------|
| `workspace/camera-lucid` | Lucid ArenaSDK ROS 2 driver |
| `workspace/ouster-ros` | Ouster ROS 2 driver |
| `workspace/twizy` | StreetDrone vehicle interface (`air_twizy_simulation`) |

Without submodules, `docker compose build` fails when assembling build contexts.

---

## 2. Configure environment variables (`.env`)

```bash
cp env.exemple .env
nano .env   # or your preferred editor
```

Compose automatically loads `.env` at the repository root.

### Key variables

| Variable | Purpose |
|----------|---------|
| `ROS_DOMAIN_ID` | Must match on host and containers (DDS isolation) |
| `ROS_DISCOVERY_SERVER` | e.g. `twizy:11811` — hostname must resolve on the host (`/etc/hosts` if needed) |
| `CAMERA_SERIALS` | Lucid serial numbers, comma-separated (`camera_1`, `camera_2`, …) |
| `SENSOR_HOSTNAME` | Ouster LiDAR IP (e.g. `10.5.5.92` on `10.5.5.0/24` — see section 3) |
| `TWIZY_CAN_PORT` | CAN interface name on the host (e.g. `can_twizy`) — becomes `CAN_PORT` inside `car` |

Discover camera serials (with image built or inside the container):

```bash
docker compose run --rm camera python3 /arena_camera_ros2/scripts/list_cameras.py
```

---

## 3. LiDAR Ethernet network (host)

On the Twizy PC, the Ouster Ethernet port (`enp11s0`) is configured to come up **automatically** with a fixed IP on the sensor subnet, without relying on generic Netplan DHCP. This avoids conflicts with another profile (`netplan-enp11s0`) and makes the LiDAR reachable as soon as the machine boots — before starting Docker.

| Item | Value on this machine |
|------|------------------------|
| Physical interface | `enp11s0` |
| NetworkManager profile | `Lidar` |
| Host (PC) IP | `10.5.5.1/24` |
| Sensor IP (`.env`) | `10.5.5.92` (`SENSOR_HOSTNAME`) |
| Auxiliary service | `dnsmasq-twizy.service` (DHCP/DNS on the LiDAR subnet) |

### 3.1 Applied configuration (NetworkManager + dnsmasq)

Run **once** on the host (or after reinstalling the OS), as root:

```bash
sudo nmcli connection modify Lidar \
  connection.interface-name enp11s0 \
  connection.autoconnect yes \
  ipv4.method manual \
  ipv4.addresses 10.5.5.1/24 \
  ipv4.gateway "" \
  ipv4.never-default yes \
  ipv4.ignore-auto-dns yes \
  ipv6.method disabled

sudo nmcli connection modify netplan-enp11s0 connection.autoconnect no

sudo nmcli connection down Lidar || true
sudo nmcli connection up Lidar

sudo systemctl enable dnsmasq-twizy.service
sudo systemctl restart dnsmasq-twizy.service
```

**What each step does:**

- **`Lidar`** — dedicated NM profile: interface `enp11s0`, manual IPv4 `10.5.5.1/24`, no default gateway (LiDAR traffic does not become the machine’s default route).
- **`netplan-enp11s0` with `autoconnect no`** — prevents Netplan from claiming the same NIC at boot.
- **`dnsmasq-twizy.service`** — keeps the Twizy auxiliary network service enabled at boot (addressing/DNS on the sensor range, per the system unit).

If the `Lidar` profile does not exist in NetworkManager yet, create it first (`nmcli connection add …`) or import the profile already used on this machine.

### 3.2 Verify LiDAR network

```bash
ip addr show dev enp11s0
systemctl status dnsmasq-twizy.service --no-pager
ping -c 3 10.5.5.92
```

Expected:

- `enp11s0` with `inet 10.5.5.1/24` and interface **UP**
- `dnsmasq-twizy.service` **active (running)** and **enabled**
- `ping` to `SENSOR_HOSTNAME` from `.env` succeeds (sensor powered, cable OK)

Then start the container:

```bash
docker compose up -d ouster_lidar
docker compose logs -f ouster_lidar
```

The service uses `network_mode: host`; it sees the same network as the host — so the configuration above must be correct **before** `docker compose up`.

**Different machine or Ethernet port:** change `enp11s0` and NM profile names; keep host and sensor on the same subnet and update `SENSOR_HOSTNAME` in `.env`.

---

## 4. CAN on the host (required for `car`)

The CAN interface belongs to **Linux on the host**. The `car` container uses `network_mode: host` and `privileged: true` to open the same interface via SocketCAN (`ros2_socketcan`).

### 4.1 Persistent names (recommended)

This repository includes udev rules for stable names instead of random `can0` / `can1` / `can2`:

| udev name | Hardware (this machine) |
|-----------|-------------------------|
| `can_twizy` | PEAK USB (Twizy bus) |
| `can_aux1` | PEAK PCIe FD, `dev_id` 0x0 |
| `can_aux2` | PEAK PCIe FD, `dev_id` 0x1 |

Install:

```bash
./install_can_udev_rules.sh
# Then: reboot OR disconnect/reconnect the PEAK USB adapter
# and reload the PEAK PCIe driver if applicable.
```

Confirm the rules match **your** hardware (`90-twizy-can-names.rules` uses machine-specific USB/PCI paths). If you change USB port or board, update the rules file before reinstalling.

In `.env`, align the port used by the stack:

```bash
TWIZY_CAN_PORT=can_twizy
```

(`socket_can_bridge.launch.xml` reads the `CAN_PORT` environment variable, set by Compose from `TWIZY_CAN_PORT`.)

### 4.2 Load drivers and bring up the interface

**PEAK USB (e.g. Twizy interface):**

```bash
sudo modprobe peak_usb
sudo ip link set can_twizy up type can bitrate 500000
```

**PEAK PCIe FD (e.g. auxiliary):** driver is usually `peak_pciefd`; use the matching udev name (`can_aux1`, `can_aux2`) and the bitrate required by your bus.

**Reference script** (adjust interface name; legacy script uses `can0`):

`workspace/twizy/ros_packages/vehicle_interface_packages/SD-VehicleInterface/can_setup.sh`

### 4.3 Verify CAN on the host

```bash
# Existing CAN interfaces
ip -br link show type can

# Details (UP state, bitrate, errors)
ip -details link show can_twizy

# Raw traffic (Ctrl+C to exit) — vehicle on / bus active
candump can_twizy

# Statistics
ip -s link show can_twizy
```

Quick interpretation:

| Symptom | Likely cause |
|---------|----------------|
| Interface missing | Driver not loaded, cable/adapter unplugged, udev not applied yet |
| `state DOWN` | Missing `ip link set … up` |
| `candump` shows no frames | Vehicle off, wrong bitrate, wrong CAN in `.env`, wiring |
| Many `bus-off` / `ERROR` | Termination, bitrate, or grounding |

**udev applied?**

```bash
ls -l /sys/class/net/can_twizy
udevadm info /sys/class/net/can_twizy | grep -E 'ID_|DEVPATH'
```

### 4.4 CAN with `car` running

```bash
docker compose up -d car
docker compose logs -f car
```

In the logs, look for `socket_can_receiver_node` / `socket_can_sender_node`:

- `interface: can_twizy` — expected interface
- `Error opening CAN receiver` — interface missing, DOWN, or wrong name in `.env`

Inside the container:

```bash
docker compose exec car bash
# ROS already sourced by the entrypoint
ros2 topic list | grep can
ros2 topic hz /from_can_bus
```

If `/from_can_bus` does not publish with the vehicle active, repeat host tests (`candump`). The issue is usually on the host interface, not ROS.

Tools in the Twizy image: `can-utils`, `cantools` (`canmonitor` alias in interactive bash).

---

## 5. X11 (RViz / graphical tools)

On the host, allow containers to access the display:

```bash
xhost +local:docker
```

For `car`, `env.exemple` uses `XAUTHORITY=/tmp/.docker.xauth`. Create the cookie if it does not exist yet (see `workspace/twizy` submodule flow).

Typical `.env` variables:

```bash
DISPLAY=:0
QT_X11_NO_MITSHM=1
```

---

## 6. Build images

From the repository root:

```bash
docker compose build                  # all services
docker compose build discovery-server
docker compose build camera
docker compose build ouster_lidar
docker compose build car
```

`ouster_lidar` builds from `workspace/ouster-ros/Dockerfile` (`ouster-ros` submodule).

---

## 7. Start services

```bash
# All (discovery + camera + lidar + car)
docker compose up -d

# Selected services only
docker compose up -d discovery-server
docker compose up -d camera
docker compose up -d ouster_lidar
docker compose up -d car
```

Suggested order on first run:

1. LiDAR network on host (section 3: `enp11s0` + `dnsmasq-twizy`, if using `ouster_lidar`)
2. CAN on host (`ip link set … up`, if using `car`)
3. `discovery-server`
4. Sensors (`camera`, `ouster_lidar`) and/or `car`

Interactive shell (no daemon):

```bash
docker compose run --rm car bash
docker compose run --rm camera bash
```

Stop:

```bash
docker compose stop
docker compose down        # removes containers (does not delete images)
```

---

## 8. Verify Docker is running correctly

### 8.1 Container status

```bash
docker compose ps
```

Expected: **STATE** column `running` (or `Up`) for the services you need.

```bash
docker ps --filter "name=discovery_server" --filter "name=air_twizy" --filter "name=ouster" --filter "name=twizy"
```

### 8.2 Logs

```bash
docker compose logs -f              # all
docker compose logs -f car
docker compose logs -f camera
docker compose logs -f ouster_lidar
docker compose logs -f discovery-server
```

Restart a service after changing `.env` or CAN:

```bash
docker compose up -d --force-recreate car
```

### 8.3 Per-service health checks

| Service | What to check |
|---------|----------------|
| `discovery-server` | No fatal errors in log; `fastdds discovery` process running |
| `camera` | `multi_camera.launch.py` log; `/camera_*/image_raw` topics |
| `ouster_lidar` | Connects to `SENSOR_HOSTNAME`; `ouster` topics (e.g. points) |
| `car` | `sd_vehicle_interface` launch; `from_can_bus` / `to_can_bus` topics |

### 8.4 ROS 2 on the host (same machine, same `ROS_DOMAIN_ID`)

With ROS Humble on the host and the **same** `ROS_DOMAIN_ID` as `.env`:

```bash
export ROS_DOMAIN_ID=0    # match .env
ros2 topic list
ros2 topic hz /camera_1/image_raw
ros2 topic hz /ouster/points   # exact name may vary by launch
ros2 topic hz /from_can_bus
```

If using the discovery server (`ROS_DISCOVERY_SERVER`, `ROS_SUPER_CLIENT` on LiDAR), configure Fast DDS on the host to match the containers.

### 8.5 Network and sensors

**GigE camera:** `network_mode: host` — the container sees the same network as the host. Ping/check camera visibility on the host before the container.

**Ouster:** network in section 3 (`enp11s0`, `10.5.5.1/24`, `dnsmasq-twizy`); then `ping` `SENSOR_HOSTNAME` from `.env` (e.g. `10.5.5.92`).

---

## 9. Quick reference — operator commands

```bash
# One-time setup
git submodule update --init --recursive
cp env.exemple .env
./install_can_udev_rules.sh    # optional, stable CAN names
# LiDAR network (section 3) — nmcli + dnsmasq-twizy; check enp11s0 and ping 10.5.5.92

# Before each run (real vehicle)
sudo modprobe peak_usb
sudo ip link set can_twizy up type can bitrate 500000
xhost +local:docker

# Build and run
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f car

# Quick CAN check
ip -br link show type can
candump can_twizy
docker compose exec car ros2 topic hz /from_can_bus

# Stop
docker compose stop
```

---

## 10. Troubleshooting

| Problem | Action |
|---------|--------|
| Build fails with empty submodule | `git submodule update --init --recursive` |
| `car` restart loop | Check CAN logs; bring interface up on host; verify `TWIZY_CAN_PORT` |
| No ROS topics on host | Mismatched `ROS_DOMAIN_ID`; multicast firewall; discovery server |
| Camera not found | `CAMERA_SERIALS`; firewall; GigE cable/network |
| LiDAR no data / no ping | Section 3: `enp11s0` UP with `10.5.5.1/24`; `dnsmasq-twizy`; `SENSOR_HOSTNAME`; cable |
| `enp11s0` has no IP after reboot | `nmcli connection up Lidar`; check autoconnect and `netplan-enp11s0` disabled |
| RViz will not open | `xhost`, `DISPLAY`, `XAUTHORITY` |
| `can0` name changes every boot | Install udev rules and use `can_twizy` in `.env` |

---

## 11. Useful files in this repository

| File | Description |
|------|-------------|
| `docker-compose.yml` | Four service definitions |
| `env.exemple` | `.env` template |
| `entrypoint_twizy.sh` | Source ROS + workspace before `car` launch |
| `entrypoint_ouster.sh` | Same for `ouster_lidar` |
| `90-twizy-can-names.rules` | CAN udev rules |
| `install_can_udev_rules.sh` | Installs rules under `/etc/udev/rules.d/` |
| `Dockerfile.server` | `discovery-server` image |

Default `car` launch (in `docker-compose.yml`): `sd_vehicle_interface` with `sd_vehicle:=twizy`, `sd_gps_imu:=peak`, `sd_speed_source:=vehicle_can_speed`.
