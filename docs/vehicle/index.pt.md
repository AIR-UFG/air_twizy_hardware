# Veículo — AIR Twizy

Stack ROS2 para o veículo StreetDrone Twizy da equipe AIR-UFG. Este workspace cobre tanto simulação (Gazebo) quanto operação real via barramento CAN.

Fonte: [AIR-UFG/air_twizy_simulation](https://github.com/AIR-UFG/air_twizy_simulation) (incluído como submódulo em `workspace/twizy`).

## Estrutura do Workspace

```
workspace/twizy/
├── docker/
│   ├── docker-compose.yml        # Compose standalone do veículo
│   └── Dockerfile
├── ros_packages/
│   ├── vehicle_interface_packages/
│   │   ├── ros2_socketcan/       # Interface CAN ROS2
│   │   └── SD-VehicleInterface/  # Integração XCU StreetDrone
│   └── vehicle_simulation_packages/
│       ├── air_description/      # Descrições URDF/mesh
│       ├── air_sim/              # Mundo Gazebo e plugins
│       └── vehicle_control_plugin/
└── utils/
    ├── run.sh                    # Lançador do container com flags de env
    ├── build_docker.sh
    ├── bash_container.sh         # Shell no container em execução
    └── record_bag.sh
```

## Início Rápido

```bash
docker compose up -d carro
docker compose exec carro bash
```

### Simulação (Gazebo)

```bash
# Dentro do container
./utils/run.sh GPU=false RVIZ=false
```

Quando o Gazebo abrir, pressione **Play**. Depois em outro terminal:

```bash
docker compose exec carro bash

# Controle por teclado
ros2 run vehicle_control sd_teleop_keyboard_control.py
```

Controles:

| Tecla | Ação |
|-------|------|
| W | Aumentar velocidade |
| S | Diminuir velocidade |
| A | Virar à esquerda |
| D | Virar à direita |
| X | Parar |

### Veículo real

```bash
# Subir interface CAN no host
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Iniciar container com CAN e interface do veículo habilitados
TWIZY_INTERFACE=true TWIZY_CAN_PORT=can0 docker compose up -d carro
```

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `TWIZY_GPU` | Habilitar GPU para processamento de nuvem de pontos | `false` |
| `TWIZY_LIDAR` | Lançar integração com LiDAR | `false` |
| `TWIZY_INTERFACE` | Lançar interface do veículo (CAN) | `true` |
| `TWIZY_CAN_PORT` | Nome da interface CAN no host | `can0` |
| `NVIDIA_RUNTIME` | Runtime NVIDIA para containers GPU | `runc` |

## Gravação

```bash
# Dentro do container
# Gravar tópicos específicos
./utils/record_bag.sh meu_run specific /velodyne_points /camera/image_raw

# Gravar todos os tópicos
./utils/record_bag.sh meu_run all
```

As bags são armazenadas em `workspace/twizy/shared_folder/` (volume montado do host).
