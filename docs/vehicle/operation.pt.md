# Operação do Veículo — Exemplo Real

Esta página documenta uma sessão real de operação no Twizy, incluindo acesso SSH via NetBird, inicialização dos containers, launch da interface do veículo e teleoperação por teclado.

## 1 — Acesso SSH via NetBird

O PC do veículo (`twizy`) é acessível pelo hostname graças ao NetBird:

```bash
ssh air@twizy
# resolve para IP NetBird: 100.122.121.134
```

Verifique se o NetBird está rodando em ambas as máquinas antes de conectar (`netbird status`).

## 2 — Iniciar os containers no veículo

```bash
# Navegar até o repositório do veículo (ajuste o caminho conforme o workspace do usuário)
cd ~/tmp_mota/air_twizy_simulation

# Iniciar ambos os containers: air_car_container + fastdds_server
./utils/run.sh
```

Saída esperada:

```
Running without NVIDIA GPU support.
[+] Running 2/2
 ✔ Container fastdds_server     Started
 ✔ Container air_car_container  Started
```

!!! warning "Executar a partir da raiz do repositório"
    `run.sh` deve ser chamado da raiz de `air_twizy_simulation/`, não de dentro de `utils/`. O script referencia internamente `docker/docker-compose.yml`.

!!! note "Avisos não bloqueantes"
    - `xhost: unable to open display` — normal ao conectar via SSH sem X forwarding. Os containers iniciam normalmente.
    - `cp: cyclonedds_vehicle.xml.template: No such file or directory` — arquivo de template ausente, não impede a operação.

## 3 — Entrar no container

```bash
./utils/bash_container.sh
# Opening bash in the container...
# root@twizy:~#
```

## 4 — Launch da interface do veículo

```bash
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy \
    sd_gps_imu:=peak \
    sd_speed_source:=vehicle_can_speed
```

Saída esperada quando a interface CAN correta está ativa:

```
[socket_can_receiver_node_exe-2] interface: can2
[socket_can_receiver_node_exe-2] applied filters: 0:0
```

A linha `applied filters: 0:0` confirma que o socket CAN está aberto e recebendo.

## Interface CAN — importante

O XCU da StreetDrone está conectado em **`can2`** neste veículo. A variável de ambiente `CAN_PORT` dentro do container já tem `can2` como padrão.

| Interface | Resultado |
|-----------|-----------|
| `can0` | `socket_can_receiver` inicia mas morre imediatamente (exit -6) |
| `can1` | `Error sending CAN message: No buffer space available` + timeout de recepção |
| `can2` | Correto — `applied filters: 0:0`, sem erros |

Se a porta errada estiver ativa, sobrescreva antes do launch:

```bash
export CAN_PORT=can2
ros2 launch sd_vehicle_interface sd_vehicle_interface.launch.xml \
    sd_vehicle:=twizy sd_gps_imu:=peak sd_speed_source:=vehicle_can_speed
```

## Variáveis de ambiente (dentro do container)

Confirmadas de um container em execução (`env`):

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

O `ROS_DISCOVERY_SERVER=twizy:11811` usa o hostname do NetBird — o container do Discovery Server (`fastdds_server`) está escutando na porta 11811.

## 5 — Teleoperação por teclado (alternativa ao controle Xbox)

Para testes rápidos sem o controle Xbox, use o script de teleop por teclado diretamente dentro do container:

```bash
# Dentro do container
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

O script publica `sd_msgs/DirectControl` em `/direct_control_cmd` em tempo real. Os valores de direção incrementam em passos de 5 por tecla pressionada (ex: segurar `a` dá -5, -10, -15, …, -55).

!!! note
    Este script requer que os nós da interface do veículo estejam rodando em um terminal separado (passo 4) para que o veículo se mova de fato. O teleop apenas publica comandos; o nó `sd_vehicle_interface` é quem os envia via CAN.

## Parar os containers

```bash
# Parar containers de fora:
docker stop air_car_container fastdds_server

# Ou usando run.sh (ele para e recria):
./utils/run.sh
```
