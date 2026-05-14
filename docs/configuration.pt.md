# Referência de Configuração

Todas as variáveis de ambiente são definidas em `.env` (copiar de `env.exemple`). O `docker-compose.yml` raiz lê esse arquivo automaticamente.

## Compartilhadas (ROS2 / DDS / X11)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DISPLAY` | Display X11 para janelas gráficas | `:0` |
| `QT_X11_NO_MITSHM` | Correção para Qt dentro do Docker | `1` |
| `ROS_DOMAIN_ID` | ID de domínio DDS do ROS2 — deve ser igual em todas as máquinas | `0` |

## Câmera (Lucid Vision)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `CAMERA_IMAGE_NAME` | Tag da imagem Docker | `air-twizy-camera:latest` |
| `CAMERA_CONTAINER_NAME` | Nome do container | `air_twizy_camera` |
| `CAMERA_RMW_IMPLEMENTATION` | Middleware ROS2 | `rmw_fastrtps_cpp` |
| `CAMERA_FASTRTPS_DEFAULT_PROFILES_FILE` | Caminho para o perfil XML FastDDS dentro do container | `/arena_camera_ros2/config/fastdds_subscriber.xml` |
| `CAMERA_SERIAL` | Número de série da câmera Lucid | _(vazio — usa a primeira encontrada)_ |
| `CAMERA_TOPIC` | Nome do tópico de imagem ROS2 | `/camera/image_raw` |

## LiDAR (Ouster)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OUSTER_ROS_DISTRO` | Distro ROS2 usado no build | `humble` |
| `OUSTER_RMW_IMPLEMENTATION` | Middleware ROS2 | `rmw_fastrtps_cpp` |
| `LIDAR_IMAGE_NAME` | Tag da imagem Docker | `air-twizy-lidar:latest` |
| `LIDAR_CONTAINER_NAME` | Nome do container | `air_twizy_lidar` |

!!! note "Parâmetros de launch do Ouster"
    Os parâmetros de launch do Ouster (`sensor_hostname`, `udp_dest`, etc.) não estão no `.env` — passe-os diretamente ao `ros2 launch` dentro do container.

## Veículo (Twizy)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `CARRO_IMAGE_NAME` | Tag da imagem Docker | `air-twizy-car:latest` |
| `CARRO_CONTAINER_NAME` | Nome do container | `air_twizy_car` |
| `TWIZY_GPU` | Habilitar GPU para processamento de nuvem de pontos | `false` |
| `TWIZY_LIDAR` | Lançar integração LiDAR dentro da stack do veículo | `false` |
| `TWIZY_INTERFACE` | Lançar interface CAN do veículo | `true` |
| `TWIZY_CAN_PORT` | Interface CAN do host (`can0`, `vcan0`, …) | `can0` |
| `NVIDIA_RUNTIME` | Runtime Docker (`runc` ou `nvidia`) | `runc` |
| `TWIZY_HOST_FOLDER_PATH` | Caminho dos pacotes ROS2 no host | `./workspace/twizy/ros_packages` |
| `TWIZY_SHARED_FOLDER` | Pasta compartilhada para bags e saídas | `./workspace/twizy/shared_folder` |
| `TWIZY_UTILS_PATH` | Caminho dos scripts utils no host | `./workspace/twizy/utils` |
| `TWIZY_XAUTHORITY` | Arquivo X11 authority para containers GPU | `/tmp/.docker.xauth` |

## Geração do perfil FastDDS

O perfil FastDDS da câmera deve ser regenerado sempre que a interface de streaming mudar:

```bash
# Lado publisher (máquina da câmera)
./workspace/camera-lucid/config/setup_fastdds.sh publisher <interface>

# Lado subscriber (máquina receptora)
./workspace/camera-lucid/config/setup_fastdds.sh subscriber <interface>
```

Isso cria `fastdds_publisher.xml` ou `fastdds_subscriber.xml` no diretório de config.
