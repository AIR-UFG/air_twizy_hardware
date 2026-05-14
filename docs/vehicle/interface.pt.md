# Pacotes de Interface do Veículo

O workspace `vehicle_interface_packages` fornece comunicação ROS2 com o hardware do StreetDrone Twizy via barramento CAN.

## Pacotes

### ros2_socketcan

Gerencia a comunicação CAN em ROS2 usando o protocolo SocketCAN.

- Implementa nós ROS2 para interfaceamento com barramento CAN
- Publica/assina mensagens `can_msgs/Frame`
- Suporta o driver SocketCAN padrão do kernel (`can0`, `vcan0`, etc.)

**Launch:**
```bash
ros2 launch ros2_socketcan socket_can_bridge.launch.xml interface:=can0
```

### SD-VehicleInterface

Integra o Xenos Control Unit (XCU) da StreetDrone com a stack de navegação ROS2.

- Traduz comandos `ackermann_msgs/AckermannDriveStamped` para frames CAN
- Publica velocidade do veículo, ângulo de direção e status
- Suporta simulação (Gazebo) e veículo real

**Tópicos assinados:**
| Tópico | Tipo | Descrição |
|--------|------|-----------|
| `/sd_control` | `ackermann_msgs/AckermannDriveStamped` | Comandos de condução |

**Tópicos publicados:**
| Tópico | Tipo | Descrição |
|--------|------|-----------|
| `/sd_status` | custom | Estado do veículo (velocidade, direção, modo) |

## Configuração do Barramento CAN

A interface CAN do host deve ser configurada antes de iniciar o container:

```bash
# CAN padrão (500 kbps — padrão StreetDrone)
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Verificar
ip link show can0
candump can0  # deve mostrar frames CAN do XCU
```

## Compatibilidade

Esses pacotes funcionam tanto em simulação quanto no veículo real:

- **Simulação**: O `SD-VehicleInterface` lê comandos e move o modelo Gazebo via plugin de controle do veículo
- **Veículo real**: Comandos são traduzidos para frames CAN e enviados ao XCU via `can0`
