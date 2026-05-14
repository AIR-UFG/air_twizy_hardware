# Teleoperação Remota

O Twizy suporta teleoperação remota via controle Xbox conectado a um laptop do operador em qualquer lugar com acesso à internet. A comunicação ocorre pela [VPN NetBird](../networking/netbird.md) e um [FastDDS Discovery Server](../networking/discovery-server.md) no veículo.

## Visão Geral do Sistema

```
OPERADOR REMOTO                          VEÍCULO (Twizy)
─────────────────────────────────────────────────────────
Controle Xbox                            FastDDS Discovery Server
     │                                         │ (porta 11811)
  joy_node                              Nós de controle do veículo
     │                                         │
direct_teleop ──── /direct_control_cmd ──► SD-VehicleInterface
                ◄── /sd_control ──────────────┘
        └─────────── VPN NETBIRD (mesh) ───────┘
```

**Fluxo de comandos:**

1. Operador envia setpoints de torque e direção via `/direct_control_cmd`
2. PC do veículo assina, aplica os comandos ao Twizy via CAN e publica o estado atual em `/sd_control`
3. O Discovery Server no veículo converte o tráfego ROS2 multicast em unicast, permitindo comunicação entre VPNs

## Requisitos

| Componente | Versão | Função |
|-----------|--------|--------|
| SO | Ubuntu 22.04 LTS | Base para ROS2 Humble |
| ROS2 Middleware | `rmw_fastrtps_cpp` | Necessário para o Discovery Server |
| VPN | NetBird (recente) | Comunicação mesh P2P |
| Containerização | Docker 24.x+ | Isolamento de ambiente |

**Hardware:**
- Operador: laptop com controle Xbox USB ou Bluetooth
- Veículo: PC de bordo conectado ao barramento CAN do Twizy
- Ambos precisam de acesso à internet para a VPN

## Procedimento de Operação

### No veículo

```bash
# 1. Verificar se o NetBird está conectado e anotar o IP
netbird status

# 2. Iniciar o Discovery Server
docker compose up -d discovery-server

# 3. Iniciar os nós de controle do veículo (assina /direct_control_cmd, publica /sd_control)
docker compose up -d carro
```

### Na máquina do operador

```bash
# 1. Verificar conectividade NetBird
ping <hostname_netbird_veiculo>

# 2. Configurar variáveis de ambiente
export ROS_DISCOVERY_SERVER=<hostname_netbird_veiculo>:11811
export ROS_SUPER_CLIENT=true
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# 3. Iniciar a stack de teleoperação
docker compose up -d

# 4. Verificar se os tópicos estão visíveis
ros2 topic list
# Deve mostrar /direct_control_cmd e /sd_control
```

## Estrutura dos Pacotes ROS2

```
ws/
├── teleop_joy_xbox/          # Pacote de teleoperação
│   ├── config/
│   │   └── xbox_controller.yaml
│   ├── launch/
│   │   ├── xbox_teleop.launch.py      # Modo 1: Twist (cmd_vel)
│   │   └── direct_teleop.launch.py    # Modo 2: Direct Control
│   └── teleop_joy_xbox/
│       ├── xbox_teleop_node.py
│       └── direct_teleop.py
└── sd_msgs/                  # Mensagens customizadas
    └── msg/
        ├── DirectControl.msg
        └── SDControl.msg
```

## Modos de Controle

### Modo 1 — Twist Padrão

```bash
ros2 launch teleop_joy_xbox xbox_teleop.launch.py
```

- Tipo de mensagem: `geometry_msgs/Twist`
- Tópico: `/cmd_vel`
- Uso: robôs móveis genéricos

### Modo 2 — Direct Control (recomendado para Twizy)

```bash
ros2 launch teleop_joy_xbox direct_teleop.launch.py
```

- Mensagens: `sd_msgs/DirectControl` (comandos), `sd_msgs/SDControl` (feedback)
- Tópicos: `/direct_control_cmd` → `/sd_control`
- Uso: controle direto de torque e direção do veículo

Veja [Controle Xbox](xbox-controller.md) para mapeamento de botões e mensagens customizadas.

## Docker Compose (lado do operador)

```yaml
services:
  discovery-server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: fastdds_server
    network_mode: "host"
    command: -i 0
    restart: unless-stopped

  teleop-client:
    build:
      context: .
      dockerfile: Dockerfile.client
    container_name: ros2_teleop_joy
    network_mode: "host"
    depends_on:
      - discovery-server
    environment:
      - ROS_DISCOVERY_SERVER=<IP_NETBIRD_VEICULO>:11811
      - ROS_DOMAIN_ID=0
      - ROS_SUPER_CLIENT=true
      - RMW_IMPLEMENTATION=rmw_fastrtps_cpp
    volumes:
      - ./ws:/root/ros2_ws/src:rw
      - /dev/input:/dev/input:rw
      - /run/udev:/run/udev:ro
    devices:
      - /dev/input
    command: ros2 run joy joy_node --ros-args -r /joy:=joy_teleop_test
```

!!! important "network_mode: host é obrigatório"
    Sem `network_mode: host`, o Docker roteia o tráfego pela sua rede bridge em vez da interface NetBird (`wt0`). Os nós ROS2 nunca conseguiriam alcançar o Discovery Server no veículo.
