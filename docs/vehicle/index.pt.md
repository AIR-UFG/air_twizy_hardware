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

---

## Pacotes de Interface do Veículo

O workspace `vehicle_interface_packages` fornece comunicação ROS2 com o hardware do StreetDrone Twizy via barramento CAN.

### ros2_socketcan

Gerencia a comunicação CAN em ROS2 usando o protocolo SocketCAN.

- Implementa nós ROS2 para interfaceamento com barramento CAN
- Publica/assina mensagens `can_msgs/Frame`
- Suporta o driver SocketCAN padrão do kernel (`can0`, `vcan0`, etc.)

```bash
ros2 launch ros2_socketcan socket_can_bridge.launch.xml interface:=can0
```

### SD-VehicleInterface

Integra o Xenos Control Unit (XCU) da StreetDrone com a stack de navegação ROS2.

- Traduz comandos `ackermann_msgs/AckermannDriveStamped` para frames CAN
- Publica velocidade do veículo, ângulo de direção e status

**Tópicos assinados:**
| Tópico | Tipo | Descrição |
|--------|------|-----------|
| `/sd_control` | `ackermann_msgs/AckermannDriveStamped` | Comandos de condução |

**Tópicos publicados:**
| Tópico | Tipo | Descrição |
|--------|------|-----------|
| `/sd_status` | custom | Estado do veículo (velocidade, direção, modo) |

### Configuração do Barramento CAN

```bash
# CAN padrão (500 kbps — padrão StreetDrone)
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Verificar
ip link show can0
candump can0  # deve mostrar frames CAN do XCU
```

---

## Operação do Veículo — Exemplo Real

### 1 — SSH no veículo

```bash
ssh air@twizy
# senha: (perguntar à equipe)
```

`twizy` resolve para `100.122.121.134` via VPN NetBird. **Ambas as máquinas devem estar com o NetBird conectado** antes de tentar (`netbird status` em cada uma).

!!! note "Primeira conexão"
    Na primeira vez que um novo computador se conecta, o SSH exibe:
    ```
    The authenticity of host 'twizy (100.122.121.134)' can't be established.
    ED25519 key fingerprint is SHA256:6KA7LU04JZoQ+1IiHqn3uDhkX+sSFLTbj2AMHe+xGgY.
    Are you sure you want to continue connecting (yes/no/[fingerprint])?
    ```
    Digite `yes` (não apenas `y` — o SSH recusa a resposta abreviada). A chave é salva permanentemente.

---

### 2 — Navegar até o repositório

O repositório fica em `~/tmp_mota/air_twizy_simulation/` no veículo. Existem diretórios similares para outros membros da equipe (`tmp_simoes/`, `tmp_victor/`) — usar o `tmp_mota/`.

```bash
cd ~/tmp_mota/air_twizy_simulation
```

Estrutura do repositório neste caminho:

```
air_twizy_simulation/
├── docker/
│   └── docker-compose.yml
├── ros_packages/
├── shared_folder/
└── utils/
    ├── run.sh              ← usar este para iniciar/reiniciar containers
    ├── bash_container.sh   ← usar este para entrar no container
    ├── record_bag.sh
    ├── direct_control/
    │   └── direct_teleop.py
    └── ...
```

---

### 3 — Iniciar os containers

```bash
# Deve ser executado da raiz de air_twizy_simulation/
./utils/run.sh
```

Saída esperada:

```
Running without NVIDIA GPU support.
[+] Running 2/2
 ✔ Container fastdds_server     Started
 ✔ Container air_car_container  Started
```

Inicia dois containers:
- `air_car_container` — container principal do veículo (ROS2 + SD-VehicleInterface)
- `fastdds_server` — FastDDS Discovery Server na porta 11811

!!! warning "NÃO usar `docker compose up` diretamente"
    Rodar `docker compose up` da raiz do repositório falha com `no configuration file provided: not found`. O compose file fica em `docker/docker-compose.yml` e requer variáveis de ambiente que só o `run.sh` configura corretamente. Use sempre `./utils/run.sh`.

!!! warning "Executar da raiz do repositório, não de dentro de `utils/`"
    O `run.sh` referencia `docker/docker-compose.yml` relativo ao diretório de trabalho. Se você estiver dentro de `utils/` ao rodar, a resolução de caminho falha. Sempre `cd ~/tmp_mota/air_twizy_simulation` primeiro.

!!! note "Avisos não bloqueantes do run.sh"
    Aparecem toda vez e podem ser ignorados:
    ```
    xhost: unable to open display ""             ← sem tela via SSH, inofensivo
    touch: /tmp/.docker.xauth: Permission denied ← mesmo motivo, inofensivo
    cp: cyclonedds_vehicle.xml.template: No such file or directory ← template ausente, não afeta operação
    ```

---

### 4 — Entrar no container

```bash
./utils/bash_container.sh
# Opening bash in the container...
# root@twizy:~#
```

Abre um shell bash dentro do `air_car_container` como root.

!!! warning "Executar `source` antes de qualquer comando `ros2`"
    O bash interativo do container **não** faz source do ROS2 automaticamente. É necessário rodar isto toda vez que abrir um novo shell dentro do container:
    ```bash
    source /opt/ros/humble/setup.bash
    ```
    Sem isso, os comandos `ros2` não serão encontrados e scripts Python que importam `rclpy` falharão silenciosamente ou com erros de import.

    Os pacotes do workspace (sd_vehicle_interface, ros2_socketcan, etc.) já são carregados pelo entrypoint do container — somente a instalação base do ROS2 precisa deste `source` manual.

---

### 5 — Launch da interface do veículo

```bash
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

Inicia três nós ROS2:
- `sd_vehicle_interface_node` — traduz comandos ROS2 para frames CAN
- `socket_can_receiver_node_exe` — lê frames CAN do barramento
- `socket_can_sender_node_exe` — escreve frames CAN no barramento

**O launch está funcionando corretamente quando aparecer:**

```
[socket_can_receiver_node_exe-2] interface: can2
[socket_can_receiver_node_exe-2] applied filters: 0:0
```

A linha `applied filters: 0:0` confirma que o socket CAN está aberto e o XCU está enviando frames. Se essa linha não aparecer em ~2 segundos após o início, a porta CAN errada está selecionada.

---

### Interface CAN — qual porta usar

O XCU da StreetDrone está fisicamente conectado em **`can2`** neste veículo. O padrão `CAN_PORT=can2` dentro do container já está correto.

| Interface | O que acontece | Significado |
|-----------|---------------|-------------|
| `can2` | `applied filters: 0:0` — sem erros | **Correto** — XCU está neste barramento |
| `can0` | `applied filters: 0:0` — mas nenhum dado do XCU trafega | Interface UP mas XCU não está conectado aqui |
| `can1` | `applied filters: 0:0` e imediatamente: `Error sending: No buffer space available` + `Error receiving: CAN Receive Timeout` | Barramento UP mas nenhum nó responde — buffer enche imediatamente |

!!! warning "`can0` e `can1` não causam crash imediato"
    As duas interfaces iniciam sem erro e mostram `applied filters: 0:0`. O problema só fica evidente ao tentar enviar um comando — com `can1` os erros aparecem imediatamente; com `can0` a interface parece saudável mas o XCU nunca recebe nem envia dados. Sempre verifique se o `applied filters: 0:0` apareceu **e** que nenhuma linha WARN veio em seguida.

Se por algum motivo o `CAN_PORT` foi alterado, redefina:

```bash
export CAN_PORT=can2
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

---

### Variáveis de ambiente dentro do container

Execute `env` dentro do container para verificar o ambiente completo. Valores confirmados em produção:

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

### 6 — Teleoperação por teclado (alternativa ao controle Xbox)

Abra um **segundo terminal** no veículo (nova sessão SSH ou painel `tmux`) e entre no container novamente:

```bash
./utils/bash_container.sh
```

Dentro do container:

```bash
source /opt/ros/humble/setup.bash
python3 utils/direct_control/direct_teleop.py
```

Saída esperada:

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

O script publica `sd_msgs/DirectControl` em `/direct_control_cmd` em tempo real.

**Comportamento da direção:**
- Cada tecla incrementa ou decrementa a direção em **5 unidades**
- O valor acumula enquanto a tecla é pressionada repetidamente: um pressionar de `a` → -5, dois → -10, etc.
- Limite máximo: **-55 a +55** (o script trava neste limite)
- Soltar a tecla **não** centraliza a direção — é preciso pressionar a direção oposta ou `x`

**Exemplo de valores observados durante um teste:**
```
Steering Value: -5.0    ← um pressionar de 'd'
Steering Value: 5.0     ← trocou para 'a'
Steering Value: 10.0
Steering Value: -55.0   ← manteve 'a' repetidamente até o limite
Steering Value: 0.0     ← voltou ao centro
```

!!! warning "Este terminal deve ser separado do terminal da interface do veículo"
    O `direct_teleop.py` apenas publica comandos. O nó `sd_vehicle_interface` (passo 5) deve estar rodando no outro terminal para de fato enviar esses comandos via CAN para o XCU.

---

### 7 — Parar os containers

**NÃO use `docker compose down`** — requer as mesmas variáveis de ambiente que o `run.sh` configura e falhará com avisos de variável não definida se chamado de um shell comum:

```
WARN: The "CAN_PORT" variable is not set. Defaulting to a blank string.
invalid spec: ::rw: empty section between colons
```

Use `docker stop` pelo nome do container:

```bash
docker stop air_car_container fastdds_server
```

Verifique que pararam:

```bash
docker ps   # deve estar vazio
```

Para reiniciar: execute `./utils/run.sh` novamente da raiz do repositório — ele para os containers existentes e os recria.
