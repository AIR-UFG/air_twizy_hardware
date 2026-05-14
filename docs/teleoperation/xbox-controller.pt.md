# Interface de Controle Xbox

A stack de teleoperação usa um controle Xbox (USB ou Bluetooth) na máquina do operador para gerar comandos de condução enviados ao veículo pela VPN NetBird.

## Mapeamento de Botões (modo Direct Control)

| Comando | Botão/Eixo | Descrição Técnica |
|---------|-----------|-------------------|
| Acelerar | RT (Gatilho Direito) | Define setpoint de torque positivo |
| Frear | LT (Gatilho Esquerdo) | Define setpoint de torque negativo |
| Direção | Analógico Esquerdo | Controla o ângulo das rodas dianteiras |
| Centralizar direção | Botão LB | Centraliza a direção imediatamente |
| Aumentar limite de velocidade | Botão Y | Aumenta o limite máximo de velocidade |
| Diminuir limite de velocidade | Botão B | Diminui o limite máximo de velocidade |
| Aumentar intensidade de frenagem | Botão X | Aumenta a força de frenagem |
| Diminuir intensidade de frenagem | Botão A | Diminui a força de frenagem |

!!! note "Direção dependente de velocidade"
    O `direct_teleop` aplica uma tabela de lookup que limita automaticamente o ângulo de direção conforme a velocidade do veículo aumenta — curvas fechadas são bloqueadas em alta velocidade.

## Mensagens ROS2 Customizadas

### DirectControl.msg (operador → veículo)

```
float64 linear_velocity    # velocidade linear (opcional)
float64 torque_setpoint    # -100 (freio total) a +100 (aceleração total)
float64 steer_setpoint     # -100 (direita) a +100 (esquerda)
```

### SDControl.msg (veículo → operador, feedback)

```
std_msgs/Header header
float64 steer              # ângulo de direção atual
float64 torque             # torque atual
float64 current_velocity   # velocidade medida do veículo
float64 target_velocity    # setpoint de velocidade alvo
int32   p, d, i, ff        # termos PID de velocidade
int32   steer_p, steer_i, steer_d  # termos PID de direção
float64 steer_actual       # ângulo de direção real do sensor
```

## Acesso ao dispositivo joystick no Docker

O container de teleop precisa de acesso aos dispositivos de entrada do host:

```yaml
volumes:
  - /dev/input:/dev/input:rw    # acesso aos drivers de entrada
  - /run/udev:/run/udev:ro      # identificação correta do joystick via udev
devices:
  - /dev/input                  # permissão explícita para o controle Xbox
```

## Verificar se o joystick está detectado

```bash
# No host (antes de iniciar o Docker)
ls /dev/input/js*
# Deve mostrar /dev/input/js0 (ou similar)

# Dentro do container
ros2 run joy joy_node --ros-args -r /joy:=joy_teleop_test
ros2 topic echo /joy_teleop_test
# Mova um analógico — os valores devem mudar na saída
```
