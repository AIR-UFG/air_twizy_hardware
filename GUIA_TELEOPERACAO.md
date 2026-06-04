# Guia de Teleoperação — Twizy

Documentação completa do projeto `air_twizy_hardware`: o que é, como está
organizado e como executar tudo, do lado do carro e do lado do operador.

---

## 1. Visão aérea

O objetivo do projeto é **dirigir um carro Twizy à distância** (e, no futuro,
de forma autônoma). Para isso ele resolve três coisas básicas:

1. **Sentir** o ambiente — câmeras, LIDAR, GPS, IMU.
2. **Agir** sobre o carro — acelerar, frear, virar.
3. **Conectar** o carro a um operador remoto.

```
        SENTIR              PENSAR / CONECTAR            AGIR
   ┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
   │ câmeras       │      │ ROS 2             │      │ carro físico │
   │ LIDAR         │─────▶│ (canais de       │─────▶│ motor        │
   │ GPS / IMU     │      │  mensagens)      │      │ direção      │
   └──────────────┘      └──────────────────┘      │ freio        │
                                  ▲                  └──────────────┘
                                  │
                          ┌───────────────┐
                          │ OPERADOR      │
                          │ (dashboard)   │
                          └───────────────┘
```

### O esqueleto: ROS 2

Tudo no meio é o **ROS 2**. Pense nele como um quadro de avisos: cada programa
pequeno (um *nó*) escreve mensagens em canais (*tópicos*) e lê de outros.
Ninguém fala diretamente com ninguém — todos se comunicam pelo quadro. Isso
deixa as peças independentes: a câmera não sabe quem lê suas imagens, e o carro
não sabe quem manda os comandos.

### Ideia central em uma frase

**O carro é um conjunto de sensores e atuadores plugados num "quadro de
mensagens" (ROS 2); qualquer um conectado a esse quadro — inclusive o operador
remoto via VPN — pode ler o que o carro sente e escrever o que ele deve fazer.**

---

## 2. Arquitetura — os dois computadores

O carro e o operador não precisam estar na mesma rede. A VPN **Netbird** cria um
túnel privado entre eles pela internet. No túnel, o carro tem o apelido `twizy`.

```
   PC DO CARRO                          PC DO OPERADOR
   (Machine A, "twizy")                 (seu PC)
┌─────────────────────────┐          ┌──────────────────────┐
│ discovery-server :11811  │◀─Netbird─│ dashboard web         │
│ camera  → /camera_N/...  │          │  (browser + teclado)  │
│ ouster  → point cloud    │          │                       │
│ car (vehicle interface)  │◀─────────│ publica controle      │
│   assina /direct_control │          │ assina câmeras        │
└─────────────────────────┘          └──────────────────────┘
```

### Como os programas se acham — Discovery Server

Normalmente nós ROS se descobrem gritando na rede local (multicast), o que não
funciona pela internet. Por isso existe o **Discovery Server**: uma lista
telefônica central. Carro e operador se registram nela (no endereço
`twizy:11811`) e assim conseguem se achar pelo túnel da Netbird.

---

## 3. As peças

### No carro (serviços Docker — `docker-compose.yml`)

| Serviço | Container | Papel |
|---|---|---|
| `discovery-server` | `discovery_server` | A lista telefônica do ROS (Fast DDS) |
| `camera` | `air_twizy_camera` | Driver das câmeras Lucid → `/camera_N/image_raw` |
| `ouster_lidar` | `ouster_lidar` | Driver do LIDAR Ouster → nuvem de pontos |
| `car` | `air_car_container` | **Vehicle interface**: ponte ROS ↔ carro via CAN |

O serviço `car` é o coração: assina `/direct_control_cmd` e traduz os comandos em
sinais elétricos no **barramento CAN** (a rede interna que fala com motor e direção).

### No operador (serviço Docker)

| Serviço | Container | Papel |
|---|---|---|
| `dashboard` | `air_twizy_dashboard` | Dashboard web de teleop (cliente do discovery server) |

O `dashboard` espelha o cliente de teleop por joystick: mesmo padrão de rede
(`network_mode: host`, Netbird), só trocando o joystick pela interface web.

---

## 4. Os fluxos

### Caminho de um comando (você aperta "W")

```
1. Você segura "W" no browser
2. JavaScript manda a cada 100 ms a lista de teclas pro Flask
3. Loop de controle (50x/s) suaviza: torque sobe gradual até o máximo
4. rclpy publica DirectControl{torque_setpoint, steer_setpoint} em /direct_control_cmd
   ─── atravessa a Netbird via discovery server ───
5. Serviço "car" recebe (DirectControl_callback)
6. Traduz pra frame CAN e envia no barramento
7. Motor acelera
```

Segurança embutida no dashboard:
- Soltou a tecla → torque volta a zero sozinho.
- Perdeu o foco da aba → todas as teclas são limpas.
- Barra de espaço → freio de emergência, zera tudo.

### Caminho de uma imagem (câmera → sua tela)

```
1. Câmera Lucid captura frame (rgb8)
2. Driver publica em /camera_1/image_raw
   ─── Netbird ───
3. dashboard.py (nó rclpy) recebe o frame
4. Converte pra JPEG (PIL)
5. Serve como MJPEG na rota /cam/1/stream
6. A tag <img> no browser mostra ao vivo
```

A telemetria (bateria, latência, sensores, logs) vai por **SSE** (`/stream`), o
servidor empurrando atualizações 10x/s. Bateria e radar ainda são dados
simulados (*mock*); câmeras e controle são reais.

---

## 5. Execução — PC do carro

### 5.1 Uma vez (preparação)

```bash
# Clonar com submódulos
git clone --recursive https://github.com/AIR-UFG/air_twizy_hardware
cd air_twizy_hardware

# Configurar variáveis
cp env.exemple .env
# editar .env:
#   CAMERA_SERIALS   = seriais das câmeras (viram camera_1, camera_2, ...)
#   TWIZY_CAN_PORT   = can_twizy
#   SENSOR_HOSTNAME  = IP do LIDAR (ex: 10.5.5.92)
#   ROS_DISCOVERY_SERVER = twizy:11811

# Rede do LIDAR (NetworkManager + dnsmasq no enp11s0, 10.5.5.0/24) — ver seção 3 do README

# Construir as imagens
docker compose build

# (uma vez) habilitar o Docker para subir no boot
sudo systemctl enable docker
```

### 5.2 A cada uso (ligar o carro)

```bash
# 1. Subir a interface CAN (ponte com motor/direção)
sudo modprobe peak_usb
sudo ip link set can_twizy up type can bitrate 500000

# 2. Liberar X11 (se for usar RViz/janelas)
xhost +local:docker

# 3. Subir todo o stack
docker compose up -d        # discovery + camera + lidar + car
```

O carro precisa estar com a **Netbird ativa** e anunciado como `twizy`.

### 5.3 Auto-start no boot

Os serviços têm `restart: unless-stopped` no compose — isso faz os containers
**voltarem sozinhos** após um reboot. Mas o gatilho depende de configuração da
máquina do carro, **não versionada no repo**:

- `sudo systemctl enable docker` — Docker sobe no boot.
- Netbird habilitada no boot.
- CAN subindo no boot (udev/systemd próprio).

Numa máquina zerada, esses passos precisam ser refeitos à mão.

### 5.4 Conferir que está no ar

```bash
docker compose ps                 # todos "Up"
candump can_twizy                 # tráfego CAN (carro ligado)
docker compose exec car ros2 topic list | grep camera
```

---

## 6. Execução — PC do operador

### 6.1 Uma vez

```bash
# 1. Instalar/entrar na Netbird (mesma rede do carro) e conferir:
ping twizy

# 2. Clonar com submódulos (precisa do código do sd_msgs)
git clone --recursive https://github.com/AIR-UFG/air_twizy_hardware
cd air_twizy_hardware
cp env.exemple .env               # só pra satisfazer o compose

# 3. Construir a imagem do dashboard
docker compose build dashboard
```

### 6.2 A cada uso

```bash
docker compose up dashboard
# abrir no browser: http://localhost:5000
```

> O `entrypoint_client.sh` faz o `source` do ROS automaticamente dentro do
> container. Você nunca digita comandos de ROS no host.

### 6.3 Câmeras

As câmeras padrão são `/camera_1/image_raw` e `/camera_2/image_raw`. Se os nomes
reais forem outros, confirme e ajuste:

```bash
# descobrir os tópicos reais (com o carro rodando)
docker compose exec car ros2 topic list | grep camera
```

E sobreponha no `docker-compose.yml`, no serviço `dashboard`:

```yaml
command: ["python3", "/root/dashboard.py", "--cam1", "/camera_1/image_raw", "--cam2", "/camera_2/image_raw"]
```

### 6.4 Controles (teclado, com a aba do browser em foco)

| Tecla | Ação |
|---|---|
| W / S | Acelerar / frear |
| A / D | Virar esquerda / direita |
| Espaço | Freio de emergência |
| I / O | Torque máximo ±10 |
| K / L | Steer máximo ±5 |

---

## 7. Quem faz o quê (resumo)

```
        CARRO (a cada sessão)                 OPERADOR (a cada sessão)
   ┌──────────────────────────────┐        ┌──────────────────────────────┐
   │ 1. CAN up (modprobe + ip link)│        │ 1. Netbird ativa (ping twizy) │
   │ 2. Netbird ativa              │        │ 2. docker compose up dashboard│
   │ 3. docker compose up -d       │◀──VPN──▶│ 3. abrir localhost:5000      │
   │    (discovery+camera+lidar+car)│        │                              │
   └──────────────────────────────┘        └──────────────────────────────┘
```

**Regra de ouro:** o carro precisa estar com o stack rodando **antes**; o
operador só vê câmeras e controla se os tópicos já estiverem sendo publicados
pelo carro.

Vários operadores podem abrir o dashboard ao mesmo tempo (cada um no seu PC),
todos lendo os mesmos tópicos. Mas se dois mandarem controle juntos, os comandos
se misturam no mesmo `/direct_control_cmd` — mantenha **um operador no controle
por vez**.

---

## 8. Troubleshooting rápido

| Sintoma | Causa provável |
|---|---|
| Dashboard abre mas câmeras "NO SIGNAL" | Carro não está publicando; ou nome de tópico errado (veja 6.3) |
| Dashboard não acha o carro | Netbird caiu (`ping twizy` falha) ou stack do carro não está no ar |
| Controle não responde | Aba do browser sem foco — clique na página |
| `car` reinicia em loop | CAN não está UP no carro (`ip -br link show type can`) |
| Containers não sobem no boot | Faltou `systemctl enable docker` na máquina do carro |

---

## 9. Arquivos relevantes deste guia

| Arquivo | Função |
|---|---|
| `dashboard.py` | Servidor Flask + nó ROS do dashboard |
| `Dockerfile.client` | Imagem do operador (compila `sd_msgs` + flask/pillow) |
| `entrypoint_client.sh` | Sourceia ROS + overlay antes de rodar o dashboard |
| `docker-compose.yml` | Define os serviços do carro e o serviço `dashboard` |
