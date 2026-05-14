# Parâmetros do Nó da Câmera

Todos os parâmetros são **somente na inicialização** — o nó deve ser reiniciado para aplicar qualquer alteração.

| Parâmetro | Tipo | Descrição | Padrão |
|-----------|------|-----------|--------|
| `serial` | int | Número de série da câmera | primeira disponível |
| `topic` | string | Nome do tópico ROS2 | `/arena_camera_node/images` |
| `pixelformat` | string | `bayer_rggb8`, `rgb8`, `bgr8`, `mono8`, … | `rgb8` |
| `width` | int | Largura da imagem em pixels | máximo da câmera |
| `height` | int | Altura da imagem em pixels | máximo da câmera |
| `gain` | float | Ganho do sensor em dB | `0.0` |
| `exposure_time` | float | Exposição em microssegundos | padrão da câmera |
| `frame_rate` | float | Taxa de aquisição alvo (FPS) | padrão da câmera |
| `trigger_mode` | bool | `true` = modo gatilho, `false` = contínuo | `false` |
| `qos_reliability` | string | `reliable` ou `best_effort` | `reliable` |

## Interação entre frame_rate e exposure_time

A taxa de frames efetiva é limitada pelo menor entre: o valor de `frame_rate` ou `1 / exposure_time`.

Para FPS máximo, mantenha a exposição curta o suficiente para permitir a taxa desejada.

**Exemplo — 33 FPS em resolução máxima:**
```bash
ros2 run arena_camera_node start --ros-args \
    -p serial:=<SEU_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8 \
    -p frame_rate:=33.0 \
    -p exposure_time:=25000
```

Exposição de 25 ms permite até 40 FPS, então o limite de `frame_rate` de 33 FPS entra em vigor.

## Usando o script de launch

```bash
# Dentro do container
./scripts/start_camera.sh <serial> <topic> <pixelformat> <largura> <altura> <ganho> <exposicao> <fps>

# Exemplo
./scripts/start_camera.sh 12345678 /camera/image_raw bayer_rggb8 "" "" 0 25000 33.0
```

Argumentos `""` vazios usam a resolução máxima da câmera.

## Múltiplas câmeras

Escale com um config YAML:

```bash
cp workspace/camera-lucid/config/cameras_example.yaml workspace/camera-lucid/config/cameras.yaml
# edite cameras.yaml com seriais e nomes de tópicos

ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py \
    config_file:=/arena_camera_ros2/config/cameras.yaml
```

!!! tip "Implantações em produção"
    Para muitas câmeras, use um switch gigabit com suporte a Jumbo Frame e configure IPs estáticos em cada câmera.
