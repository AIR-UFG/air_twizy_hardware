# Primeiros Passos

## Pré-requisitos

- **Docker** e **Docker Compose** v2+
- **Git** com suporte a submódulos
- Ubuntu 22.04 ou superior (recomendado)
- Para câmera: câmera Lucid Vision Triton com Ethernet GigE
- Para LiDAR: sensor Ouster OS-series em Ethernet
- Para veículo: interface CAN (`can0`) ligada ao XCU StreetDrone Twizy

## 1 — Clonar o repositório

```bash
git clone https://github.com/AIR-UFG/air_twizy_hardware.git
cd air_twizy_hardware
git submodule update --init --recursive
```

!!! tip "ArenaSDK (somente câmera)"
    O submódulo da câmera Lucid exige que os arquivos do ArenaSDK e arena_api sejam colocados manualmente antes do build:

    - `ArenaSDK_Linux_x64.tar.gz` → `workspace/camera-lucid/resources/ArenaSDK/linux64/`
    - `arena_api-*.whl` → `workspace/camera-lucid/resources/arena_api/`

    Baixe os dois no [Lucid downloads hub](https://thinklucid.com/downloads-hub/).

## 2 — Configurar variáveis de ambiente

```bash
cp env.exemple .env
```

Edite `.env` com os valores da sua máquina. No mínimo:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `CAMERA_SERIAL` | Número de série da câmera Lucid | `12345678` |
| `ROS_DOMAIN_ID` | Domínio ROS2 compartilhado (deve ser igual em todas as máquinas) | `0` |
| `TWIZY_CAN_PORT` | Nome da interface CAN no host | `can0` |

Veja [Configuração](configuration.md) para a referência completa de variáveis.

## 3 — Build das imagens Docker

```bash
# Build dos três serviços
docker compose build

# Ou individualmente
docker compose build camera
docker compose build lidar
docker compose build carro
```

## 4 — Configuração de hardware

=== "Câmera (GigE)"
    ```bash
    # Ajustar interface GigE (MTU, buffers de recepção, ring)
    sudo ./workspace/camera-lucid/scripts/setup_network.sh <interface-gige>

    # Atribuir IP link-local à interface
    sudo ip addr add 169.254.1.1/16 dev <interface-gige>

    # Permitir que containers abram janelas gráficas
    xhost +local:docker
    ```

=== "LiDAR (Ouster)"
    Conecte o sensor Ouster ao host via Ethernet. O sensor auto-configura um IP
    link-local por padrão. Use `avahi-resolve -n <hostname>.local` ou verifique
    seu servidor DHCP para encontrar o IP antes de iniciar.

=== "Veículo (CAN)"
    Suba a interface CAN antes de iniciar o container:
    ```bash
    sudo ip link set can0 type can bitrate 500000
    sudo ip link set can0 up
    ```

## 5 — Iniciar os serviços

```bash
# Iniciar tudo
docker compose up -d

# Ou um serviço específico
docker compose up -d camera
docker compose up -d lidar
docker compose up -d carro
```

## 6 — Shell interativo

```bash
docker compose exec camera bash
docker compose exec lidar bash
docker compose exec carro bash
```

## Parar os serviços

```bash
docker compose down
```
