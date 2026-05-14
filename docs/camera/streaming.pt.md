# Streaming Multi-máquina

Transmita imagens da câmera para um receptor remoto via LAN ou VPN.

## Por que perfis FastDDS são necessários

Quando uma máquina tem múltiplas interfaces de rede (ex: porta GigE da câmera + WiFi), o FastDDS anuncia todos os IPs como localizadores de dados. O assinante remoto pode então tentar enviar ACKs para o IP GigE da câmera (169.254.x.x), que não é acessível remotamente.

Perfis unicast FastDDS restringem qual IP é anunciado. O perfil do publisher também inclui o endereço de loopback (`127.0.0.1`) para que processos co-localizados (ex: relay de compressão) se comuniquem em velocidade máxima.

## Comparação de largura de banda

| Método | Resolução | Taxa | Banda | Notas |
|--------|-----------|------|-------|-------|
| RAW limitado | 1024×768 | 15 FPS | ~12 Mbps | Somente baixa resolução |
| JPEG comprimido q=80 | 2048×1536 | 33 FPS | ~35–45 Mbps | Res. máxima em taxa máxima (WiFi OK) |
| RAW completo | 2048×1536 | 33 FPS | ~825 Mbps | Requer link GbE |

A compressão JPEG é a abordagem recomendada para streaming.

## Configuração

### Máquina da câmera (publisher)

```bash
# Gerar perfil FastDDS para a interface de streaming
./workspace/camera-lucid/config/setup_fastdds.sh publisher <interface-streaming>
# Exemplo: ./config/setup_fastdds.sh publisher wlan0

# Iniciar nó da câmera em FPS máximo
./workspace/camera-lucid/scripts/start_camera.sh <serial> /camera/image_raw bayer_rggb8 "" "" 0 25000 33.0

# Iniciar relay de compressão (terminal separado ou background)
bash ./workspace/camera-lucid/notebook_setup/compress_stream.sh /camera/image_raw
```

### Máquina receptora (Docker)

```bash
# Gerar perfil FastDDS para a interface receptora
./workspace/camera-lucid/config/setup_fastdds.sh subscriber <interface-receptora>
# Exemplo: ./config/setup_fastdds.sh subscriber eth0

# Permitir tráfego no firewall (se necessário)
sudo bash ./workspace/camera-lucid/notebook_setup/setup_firewall_receiver.sh 192.168.X.0/24

xhost +local:docker
docker compose up -d camera
docker compose exec camera bash

# Dentro do container
source /opt/ros/humble/setup.bash
python3 /arena_camera_ros2/notebook_setup/stream_viewer.py \
    --topic /camera/image_raw --compressed
```

## Streaming via VPN (NetBird / WireGuard)

O projeto Twizy usa o **NetBird** como VPN — veja [Configuração do NetBird](../networking/netbird.md). O descobrimento por multicast não funciona através de nenhum túnel VPN. Use o [FastDDS Discovery Server](../networking/discovery-server.md) (recomendado) ou adicione `initialPeersList` manualmente com o IP VPN do peer remoto:

```xml
<!-- Adicionar dentro de <rtps> no fastdds_publisher.xml -->
<initialPeersList>
  <locator>
    <udpv4>
      <address>10.X.X.X</address>  <!-- IP VPN do peer remoto -->
      <port>11811</port>
    </udpv4>
  </locator>
</initialPeersList>
```

## Solução de Problemas

**Tópico visível mas 0 frames recebidos:**

- Causa mais comum: FastDDS anunciando o IP da interface errada
- Execute `setup_fastdds.sh` em ambas as máquinas com a interface correta
- Confirme com `tcpdump -i any udp port 7400` que os pacotes chegam na interface certa
- O perfil FastDDS do assinante deve usar o IP onde os pacotes fisicamente chegam (verifique com `tcpdump`)

**Receptor Fedora Kinoite / Silverblue (Toolbox):**

Veja o [README do notebook_setup](https://github.com/AIR-UFG/air_twizy_hardware/tree/main/workspace/camera-lucid/notebook_setup) para o procedimento completo via Toolbox.
