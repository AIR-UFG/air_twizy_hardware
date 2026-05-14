# Câmera — Lucid Vision Triton

Driver ROS2 Humble para câmeras Lucid Vision Triton (GigE Vision), empacotado como container Docker. Suporta configurações com uma ou múltiplas câmeras, streaming JPEG comprimido via LAN ou VPN, gravação de bags e exportação de vídeo.

Adaptado do [driver oficial Lucid Vision ROS2](https://github.com/lucidvisionlabs/arena_camera_ros2) (originalmente para ROS2 Eloquent).

## Requisitos

- Câmera Lucid Vision Triton conectada via GigE (Ethernet)
- Arquivos ArenaSDK e arena_api em `resources/` (veja [Primeiros Passos](../getting-started.md))
- Interface GigE configurada com `scripts/setup_network.sh`

## Início Rápido

```bash
# Configurar interface GigE (executar no host, não dentro do container)
sudo ./workspace/camera-lucid/scripts/setup_network.sh <interface-gige>
sudo ip addr add 169.254.1.1/16 dev <interface-gige>

xhost +local:docker
docker compose up -d camera
docker compose exec camera bash

# Dentro do container — verificar se a câmera é detectada
python3 /arena_camera_ros2/scripts/list_cameras.py

# Iniciar nó da câmera
ros2 run arena_camera_node start --ros-args \
    -p serial:=<SEU_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8
```

## Estrutura de Diretórios

```
workspace/camera-lucid/
├── Dockerfile                      # Imagem ROS2 Humble + ArenaSDK
├── docker-compose.yml              # Compose standalone da câmera
├── config/
│   ├── setup_fastdds.sh            # Gera perfis unicast FastDDS
│   ├── cameras_example.yaml        # Template de config multi-câmera
│   └── fastdds_*.xml               # Perfis FastDDS
├── scripts/
│   ├── setup_network.sh            # Ajuste de interface GigE (MTU, buffers, ring)
│   ├── list_cameras.py             # Detectar câmeras conectadas
│   ├── start_camera.sh             # Lançador do nó da câmera
│   ├── compress_bayer_stream.py    # Relay de compressão JPEG
│   ├── focus_helper.py             # Score de foco ao vivo
│   ├── record_video.py             # Gravação direta em MP4
│   ├── bag_to_video.py             # Converter bag ROS2 para MP4
│   └── convert_bag.py              # Wrapper de bag-para-vídeo
├── notebook_setup/                 # Ferramentas para o receptor
├── launch/
│   ├── multi_camera.launch.py      # Lançar múltiplas câmeras por YAML
│   └── camera_streaming.launch.py  # Launch otimizado para streaming
└── ros2_ws/src/
    └── arena_camera_node/          # Nó ROS2 em C++ encapsulando ArenaSDK
```

## Formato Bayer RAW

Câmeras Triton produzem BayerRG8 nativamente. Use `pixelformat:=bayer_rggb8` para dados RAW sem cópia. Ao processar no OpenCV:

```python
# bayer_rggb8 no ROS2 corresponde a BayerBG no OpenCV (nomes invertidos)
bgr = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)
```

## Solução de Problemas

**Câmera não detectada:**

- Verifique o cabo Ethernet e a alimentação da câmera
- Execute `sudo ./scripts/setup_network.sh <interface>` no host
- Verifique se o IP do host está na mesma sub-rede: `ip addr show`
- Tente `ping <ip-da-camera>`

**Imagem cinza ou sem foco:**

- Câmeras Triton não vêm com lente — é necessário instalar uma lente C-mount separadamente
- Ajuste o foco: `python3 /arena_camera_ros2/scripts/focus_helper.py`

**Nenhuma janela gráfica:**

- Execute `xhost +local:docker` no host antes de iniciar o container

**Erro de compilação: `True not declared`:**

- Corrigido neste repositório (driver upstream tinha `True` do Python em código C++)
