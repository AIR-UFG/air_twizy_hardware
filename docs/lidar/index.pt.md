# LiDAR — Ouster

Driver ROS2 para sensores LiDAR Ouster OS-series, empacotado como container Docker.

Fonte: [ouster-lidar/ouster-ros](https://github.com/ouster-lidar/ouster-ros) (incluído como submódulo).

## Requisitos

- Sensor Ouster OS-series conectado via Ethernet
- Hostname ou IP do sensor conhecido (use `avahi-resolve -n <hostname>.local` para link-local)

## Início Rápido

```bash
docker compose up -d lidar
docker compose exec lidar bash

# Dentro do container — iniciar o driver
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch ouster_ros sensor.composite.launch.xml \
    sensor_hostname:=<IP_OU_HOSTNAME_DO_SENSOR>
```

## Tópicos Publicados

| Tópico | Tipo | Descrição |
|--------|------|-----------|
| `/ouster/points` | `sensor_msgs/PointCloud2` | Nuvem de pontos 3D |
| `/ouster/imu` | `sensor_msgs/Imu` | Dados de IMU |
| `/ouster/scan` | `sensor_msgs/LaserScan` | Fatia 2D do scan |
| `/ouster/image` | `sensor_msgs/Image` | Imagem de range/intensidade |

## Parâmetros Principais

| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| `sensor_hostname` | IP ou hostname do sensor | `os-XXXX.local` ou IP |
| `lidar_mode` | Resolução e taxa de scan | `512x10`, `1024x10`, `1024x20`, `2048x10` |
| `point_type` | Formato dos campos da nuvem | `original`, `xyz`, `xyzi`, `xyzir` |
| `proc_mask` | Habilitar/desabilitar tipos de mensagem | `IMU\|PCL\|SCAN\|IMG\|RAW\|TLM` |
| `use_system_default_qos` | QoS padrão (necessário para rosbag) | `false` (padrão) |
| `min_range` / `max_range` | Filtro de alcance em metros | `0.0` / `1000.0` |

Referência completa de parâmetros: `workspace/ouster-ros/ouster-ros/config/driver_params.yaml`

## Gravação de Bag

```bash
# Dentro do container do lidar
ros2 bag record /ouster/points /ouster/imu -s mcap -o bag_ouster
```

## Replay de bag ou PCAP

```bash
# De bag ROS2
ros2 launch ouster_ros replay.composite.launch.xml bag_file:=/caminho/para/bag

# De PCAP
ros2 launch ouster_ros replay_pcap.launch.xml \
    pcap_file:=/caminho/para/arquivo.pcap \
    metadata:=/caminho/para/metadata.json
```

## Visualização

```bash
# Iniciar com RViz
ros2 launch ouster_ros sensor.composite.launch.xml \
    sensor_hostname:=<IP> viz:=true
```

## Solução de Problemas

**Nenhum dado recebido:**

- Verifique se o sensor está acessível: `ping <sensor_hostname>`
- Verifique `udp_dest` — se o host tem múltiplas interfaces, especifique o IP da interface onde os pacotes UDP devem chegar
- Certifique-se de que nenhum firewall está bloqueando as portas UDP usadas pelo sensor

**Timestamps errados:**

- Configure `timestamp_mode` para `TIME_FROM_ROS_TIME` se o sensor não tiver sincronização GPS
