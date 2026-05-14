# FastDDS Discovery Server

O ROS2 padrão depende de multicast para descoberta de nós, o que não funciona através de túneis VPN ou entre máquinas em redes diferentes. A solução é um **FastDDS Discovery Server centralizado** rodando no veículo, com o qual todos os nós (locais e remotos) se registram via unicast.

## Como funciona

```mermaid
sequenceDiagram
    participant V as PC do Veículo
    participant DS as Discovery Server (porta 11811)
    participant O as Operador Remoto

    V->>DS: registrar nós (local, via 127.0.0.1 ou wt0)
    O->>DS: registrar nós (via IP NetBird)
    DS-->>V: lista de peers
    DS-->>O: lista de peers
    V<-->>O: troca de tópicos ROS2 (unicast)
```

## Configuração no veículo

### Dockerfile.server

```dockerfile
FROM ros:humble-ros-core
RUN apt-get update && apt-get install -y \
    ros-humble-rmw-fastrtps-cpp \
    fastdds-tools \
    && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["fastdds", "discovery"]
```

### docker-compose.yml (lado do veículo)

```yaml
services:
  discovery-server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: fastdds_server
    network_mode: "host"        # obrigatório para acessar interface wt0 do NetBird
    command: -i 0               # ID do servidor de descoberta 0
    restart: unless-stopped
```

Iniciar:

```bash
docker compose up -d discovery-server
```

Ou sem Docker:

```bash
source /opt/ros/humble/setup.bash
fastdds discovery -i 0
```

!!! warning "Conflito com interface GigE da câmera"
    Executar o Discovery Server sem vinculá-lo a uma interface específica fazia com que ele anunciasse na interface GigE da câmera (`169.254.x.x`), bloqueando as conexões da câmera. Usar `network_mode: host` combinado com o perfil FastDDS exclusivo do NetBird resolve esse problema.

## Variáveis de ambiente

### Lado do veículo

```bash
# Sem variáveis especiais de Discovery Server — ele é o próprio servidor
ROS_DOMAIN_ID=0
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

### Lado do operador

```bash
ROS_DISCOVERY_SERVER=<hostname_ou_ip_netbird_do_veiculo>:11811
ROS_SUPER_CLIENT=true        # desativa multicast, força uso exclusivo do Discovery Server
ROS_DOMAIN_ID=0
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `ROS_DISCOVERY_SERVER` | `hostname:11811` | Hostname ou IP NetBird da máquina com o servidor |
| `ROS_DOMAIN_ID` | `0` | Deve ser idêntico em todas as máquinas da rede |
| `ROS_SUPER_CLIENT` | `true` | Desativa multicast, força uso exclusivo do Discovery Server |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | Define o FastDDS como middleware ROS2 |

## Verificação

```bash
# Em qualquer máquina com as variáveis configuradas:
ros2 topic list
# Deve mostrar os tópicos do veículo
```
