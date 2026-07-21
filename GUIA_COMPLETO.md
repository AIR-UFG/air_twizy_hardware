# Guia Completo — Interface de Teleoperação do Twizy

Como funciona a interface web que dirige e monitora o Renault Twizy autônomo do AIR-UFG
à distância. Este guia começa do zero (sem assumir conhecimento) e vai aprofundando até os
detalhes técnicos no final. Leia só a Parte 1 se você só quer entender e usar; as Partes 2 e 3
são para quem vai mexer no código ou no carro.

Índice:
- Parte 1 — Entendendo (linguagem simples)
- Parte 2 — Usando na prática
- Parte 3 — Detalhes técnicos

---

# PARTE 1 — Entendendo (para leigos)

## 1.1 O que é isso?

É um **site** (uma página que abre no navegador, tipo Chrome) que funciona como o "painel de
controle" de um carro de verdade. Você abre a página no seu computador e, por ela, consegue:

- **Ver** o que o carro "enxerga": câmeras e o sensor LiDAR (um sensor que mede distâncias em 360°).
- **Dirigir** o carro à distância: acelerar, frear e virar, usando o teclado.

O carro (um Renault Twizy adaptado para ser autônomo) pode estar em outro lugar — outra sala,
outro prédio, outra cidade. Você controla ele pela internet, com segurança.

## 1.2 A ideia geral, com uma analogia

Imagine o carro como uma **pessoa** e você como alguém do outro lado do mundo tentando guiá-la
por telefone. Para isso funcionar, três coisas precisam acontecer:

1. **A pessoa precisa te contar o que vê** → as câmeras e o LiDAR do carro.
2. **Você precisa dar ordens** → "acelera", "vira à esquerda" (as teclas W A S D).
3. **Vocês precisam de uma linha telefônica** → uma conexão de internet privada e segura.

A interface é justamente esse "telefone com vídeo": ela mostra o que o carro vê e leva as suas
ordens até ele.

## 1.3 As peças e como se conectam

Existem **dois computadores** envolvidos:

```
   O CARRO (fica com o veículo)                    VOCÊ (seu PC)
   ┌──────────────────────────────┐              ┌───────────────────────┐
   │ - câmeras                     │              │  navegador (Chrome)    │
   │ - LiDAR                       │   internet   │  mostrando a interface │
   │ - computador de bordo         │◀────VPN─────▶│  você aperta W/A/S/D   │
   │ - liga no motor/direção       │  (Netbird)   │                        │
   └──────────────────────────────┘              └───────────────────────┘
```

- **VPN (Netbird):** é a "linha telefônica privada". A internet comum é pública; a VPN cria um
  túnel fechado entre o seu PC e o carro, como se os dois estivessem na mesma rede caseira,
  mesmo estando longe. Sem estar na VPN, seu PC não acha o carro.
- **O carro tem um apelido na VPN: `twizy`.** É por esse apelido (ou pelo número de IP dele) que
  o seu PC encontra o carro.

## 1.4 O que aparece na tela

Quando você abre a interface (`http://localhost:5000`), vê:

- **Três câmeras** na parte de cima (esquerda, centro, direita) — a visão da frente do carro.
- **TOP VIEW (vista de cima):** um painel redondo que mostra o **LiDAR**. Ele tem **abas** para
  trocar o tipo de visualização:
  - *Nuvem* — pontinhos vistos de cima, como um radar, mostrando os obstáculos ao redor.
  - *Range* — uma imagem colorida onde a cor indica a distância (perto/longe).
  - *Signal / Near-IR / Reflec* — imagens em tons de cinza, como fotos "especiais" que o LiDAR
    consegue tirar do ambiente (brilho, reflexo, luz infravermelha).
- **Barras de controle:** mostram quanto de aceleração (torque) e de esterço (direção) estão
  sendo enviados.
- **Logs:** mensagens de texto do sistema (o que está acontecendo por baixo).
- **Status/bateria** no topo.

## 1.5 Como dirigir

Primeiro, **clique em qualquer lugar da página** (para o navegador "prestar atenção" no teclado).
Depois:

| Tecla | O que faz |
|-------|-----------|
| **W** | acelera para frente |
| **S** | freia / dá ré |
| **A** | vira para a esquerda |
| **D** | vira para a direita |
| **Espaço** | **freio de emergência** (para tudo na hora) |
| I / O | aumenta / diminui o limite de aceleração |
| K / L | aumenta / diminui o limite de esterço |

Segurança embutida: se você **soltar** a tecla, o carro desacelera sozinho; se você **trocar de
aba** do navegador, todas as teclas são "soltas" automaticamente; e o **Espaço** freia na hora.

## 1.6 Por que as imagens são "quadradas" / de baixa qualidade?

A "linha telefônica" (VPN pela internet) é **estreita** — passa pouca informação por segundo.
As câmeras e o LiDAR do carro geram uma quantidade GIGANTE de dados (muito mais do que a linha
aguenta). Se tentássemos mandar tudo, travava tudo.

Solução: **o próprio carro encolhe as imagens antes de enviar** — diminui o tamanho, comprime,
e manda poucas por segundo. É por isso que a imagem chega pequena/simples: é o preço de caber na
linha estreita. Esse "encolhedor" que roda no carro se chama **relay** (explicado na Parte 3).

## 1.7 Importante sobre segurança

O controle é **real**. Se o carro estiver ligado, destravado e em marcha (Drive), apertar **W**
faz ele **acelerar de verdade**. Por isso:

- Sempre tem que haver um **piloto de segurança dentro do carro**, pronto para assumir.
- Use o **Espaço** (freio de emergência) a qualquer sinal de problema.
- A interface só move o carro se ele estiver **armado** (modo autônomo) e **em Drive** — senão os
  comandos chegam mas o carro não anda (é uma trava de segurança do próprio veículo).

---

# PARTE 2 — Usando na prática

## 2.1 Do que você precisa (uma vez)

1. **Um PC com Linux** e **Docker** instalado (o Docker é um programa que roda a interface dentro
   de uma "caixinha" isolada, sem você precisar instalar mil coisas). Confira:
   ```bash
   docker --version && docker compose version
   ```
2. **Netbird conectado** à rede do projeto. Confira:
   ```bash
   netbird status         # tem que estar "Connected"
   ping 100.122.121.134   # o carro tem que responder
   ```
   Se não tiver Netbird ou o convite da rede, peça ao responsável pelo projeto.

## 2.2 Rodando

Dentro da pasta do pacote:
```bash
./run.sh
```
Na primeira vez ele "monta" a interface (demora alguns minutos, baixando o necessário). Depois é
só abrir no navegador:

**http://localhost:5000**

Para parar:
```bash
docker compose down
```

## 2.3 Se algo der errado

| O que você vê | Provável causa | O que fazer |
|---------------|----------------|-------------|
| Abre, mas tudo "NO SIGNAL" | Carro offline, ou os "relays" pararam no carro | `ping 100.122.121.134`; se ok, peça pra alguém com acesso religar os relays |
| Câmeras/LiDAR travando | Internet ruim (VPN instável) | Normal em rede fraca; melhora sozinho |
| Aperto as teclas e nada | A página está sem "foco" | Clique na página primeiro |
| Dirijo mas o carro não anda | Carro em Park/Neutro (não em Drive) | Alguém precisa pôr o câmbio em Drive no carro |
| `run.sh` falha ao montar | Sem internet pra baixar a base | Conecte à internet e tente de novo |

---

# PARTE 3 — Detalhes técnicos

## 3.1 Arquitetura

Tudo roda sobre **ROS 2 Humble** — um "sistema nervoso" para robôs. Programas pequenos (*nós*)
publicam mensagens em canais nomeados (*tópicos*) e assinam os canais que interessam. Ninguém
fala direto com ninguém: todos se comunicam pelo "quadro de avisos" do ROS.

```
 CARRO (peer Netbird "twizy", IP 100.122.121.134)     OPERADOR (seu PC)
 ┌───────────────────────────────────────────┐       ┌──────────────────────────┐
 │ discovery_server  (Fast DDS, porta 11811)  │◀─VPN─▶│ container do dashboard    │
 │ air_twizy_camera  → /camera/*/image_raw     │       │  (Flask + nós rclpy)      │
 │ ouster_lidar      → /ouster/points, imgs    │       │  http://localhost:5000    │
 │ twizy (sd_vehicle_interface) ← /direct_control_cmd  │  publica controle         │
 │      └─ traduz p/ CAN → motor/direção       │◀──────│  assina câmeras/lidar     │
 │ + relays (encolhem os dados)                │       └──────────────────────────┘
 └───────────────────────────────────────────┘
```

- **Fast DDS Discovery Server:** normalmente os nós ROS se descobrem por *multicast* na rede local,
  o que não funciona pela internet/VPN. O Discovery Server é uma "lista telefônica" central (roda
  no carro, porta 11811); carro e operador se registram nele e assim se acham pelo túnel. O
  dashboard aponta para ele com `ROS_DISCOVERY_SERVER=100.122.121.134:11811` e `ROS_SUPER_CLIENT=true`.
- **RMW:** `rmw_fastrtps_cpp` (implementação DDS usada dos dois lados).

## 3.2 Fluxo de um comando (você aperta W)

```
1. Navegador: a cada 150 ms manda a lista de teclas pressionadas (POST /control) ao Flask.
   (não manda nada quando não há tecla pressionada — economia)
2. Loop de controle no servidor (50 Hz) suaviza: torque sobe gradualmente até o limite.
3. Nó rclpy publica DirectControl{linear_velocity, torque_setpoint, steer_setpoint}
   no tópico /direct_control_cmd.
   ─── atravessa a VPN via discovery server ───
4. Serviço "twizy" (sd_vehicle_interface) recebe (callback DirectControl).
5. Traduz para quadros CAN e envia no barramento can_twizy (400 Hz).
6. Motor/direção respondem — SE o veículo estiver armado e em Drive.
```

Mensagem de controle — `sd_msgs/DirectControl` (3 campos):
```
float64 linear_velocity   # setpoint de velocidade (o dashboard deixa 0 → usa torque)
float64 torque_setpoint   # -100 (freio máx) a +100 (aceleração máx)
float64 steer_setpoint    # -100 a +100 (esterço)
```
O dashboard publica **exatamente no mesmo tópico e tipo** que os scripts `direct_teleop.py` e
`direct_teleop_gui.py` (todos em `direct_control_cmd`), que a `sd_vehicle_interface` assina.

## 3.3 Por que o carro pode não andar (controle real)

Mesmo com o comando chegando, o veículo StreetDrone só se move se:
- **Estiver armado** (modo autônomo). No CAN: `Torque_Automation_Granted = 1`,
  `Steer_Automation_Granted = 1`. O MCU pisca amarelo quando armado.
- **Estiver em Drive.** No CAN: `PRND_Actual_Zs` (marcha atual, mensagem `StreetDrone_Data_2`,
  ID 279). Se estiver **0 (Park/Neutro)**, torque positivo não move — trava de segurança.
  O software da interface NÃO seleciona marcha (o `PRND_Request_Zs` é sinal órfão no DBC); a
  marcha muda pelo **seletor físico** do Twizy.

Diagnóstico do estado (decodificando o CAN com `cantools` no container do carro): ver
`candecode.py` nos backups do projeto.

## 3.4 Fluxo de uma imagem e os RELAYS (o coração do sistema)

A VPN entrega ~0.2–1 Mbps. Os dados brutos são enormes: cada câmera raw ≈ 253 Mbps; a nuvem do
LiDAR ≈ 16 MB/s (~128 Mbps). **Nada disso passa pela VPN.** Por isso o carro roda "relays": nós
que assinam o tópico pesado localmente, **reduzem**, e publicam um tópico pequeno que o dashboard
assina pela VPN. Padrão:
```
tópico pesado (local no carro) → [relay: reduz/comprime] → tópico pequeno → VPN → dashboard
```
Todos usam QoS **BEST_EFFORT** (tolera perda, não trava retransmitindo) e limitam a taxa (fps).

Os três relays (pasta `relays/`), rodam via `docker exec -d` dentro de containers do carro:

| Relay | Container | Assina | Faz | Publica |
|---|---|---|---|---|
| `cam_compress_relay.py` | air_twizy_camera | `/camera/<n>/image_raw` (bayer 2048×1536, 10 Hz, 3 MB) | debayer → 320px → rotaciona 180° → JPEG q40 | `/camera/<n>/image_raw/compressed` (3 fps, ~4 KB) |
| `lidar_topdown_relay.py` | ouster_lidar | `/ouster/points` (PointCloud2, ~16 MB/s) | parse x,y,z → filtra raio 0.8–20 m → decima ≤300 pts | `/lidar/topdown` (Float32MultiArray, 2.5 Hz, ~2.4 KB) |
| `lidar_img_relay.py` | ouster_lidar | 4 panoramas `/ouster/*_image` (mono16 128×1024) | normaliza 8-bit → colormap → 384px → JPEG q30 | `/ouster/<n>_image/compressed` (0.5 fps, ~10 KB) |

O dashboard **só assina os tópicos pequenos** (`.../compressed` e `/lidar/topdown`) — nunca os
brutos. Consumo típico na VPN: ~60–90 KB/s.

Limitação: os relays são **temporários** (não sobrevivem a reboot/recreate dos containers).
Religue-os com `car-relays/start_car_relays.sh air@twizy` (precisa de acesso SSH ao carro).

## 3.5 Anatomia do `dashboard.py`

Um único arquivo Python. Estrutura:

- **Nós ROS (rclpy):**
  - `TeleopNode` — publica `DirectControl` em `direct_control_cmd`.
  - `CameraNode` (1 por câmera) — assina imagem comprimida ou raw; guarda o último frame JPEG.
  - `LidarNode` — assina `/lidar/topdown` (Float32MultiArray); guarda a lista de pontos.
  - `LidarImgNode` (1 por panorama) — assina `/ouster/<n>_image/compressed`; guarda o JPEG.
  - Todos giram num `MultiThreadedExecutor` numa thread separada.
- **Loop de controle (50 Hz):** suaviza torque/esterço a partir das teclas seguradas, aplica
  freio de emergência (torque negativo) e publica.
- **Servidor Flask:**
  - `/` — serve a página (HTML+CSS+JS embutidos), com `Cache-Control: no-store`.
  - `/control` (POST) — recebe teclas / ajustes / emergência.
  - `/stream` — **SSE** (Server-Sent Events): empurra 10x/s um JSON com torque, esterço, sensores,
    logs e os **pontos do LiDAR** (`lidar`).
  - `/cam/<id>/stream` — MJPEG das câmeras.
  - `/lidarimg/<nome>.jpg` — um JPEG do panorama do LiDAR (atualizado a cada 1 s pelo JS, sem
    stream persistente — evita estourar o limite de conexões do navegador).
- **Front-end (JS embutido):**
  - `EventSource('/stream')` recebe o SSE e atualiza barras, sensores, logs e o canvas.
  - `drawRadar()` desenha os pontos do LiDAR no `<canvas>` (aba Nuvem), em vista de cima.
  - `setLidarTab(nome)` troca entre a Nuvem (canvas) e os panoramas (imagem JPEG).
  - Teclado: envia teclas a 150 ms; solta tudo ao perder foco; Espaço = emergência.

## 3.6 Tópicos ROS relevantes

- Controle: `/direct_control_cmd` (sd_msgs/DirectControl). QoS RELIABLE/VOLATILE. Saída CAN em `/to_can_bus` (400 Hz).
- Câmeras: `/camera/top_left|top_front|top_right/image_raw` (+ `/compressed` do relay).
- LiDAR: `/ouster/points` (PointCloud2); `/ouster/range_image|signal_image|nearir_image|reflec_image`
  (Image mono16 128×1024); `/ouster/scan`, `/ouster/imu`; `/lidar/topdown` (do relay).
- Telemetria do veículo: `/current_velocity`, `/sd_current_twist`, `/sd_current_GPS`, `/sd_imu_raw`, `/sd_control`.

## 3.7 Rede e imagem Docker

- O container do dashboard sobe com `network_mode: host` (obrigatório para o tráfego rotear pela
  interface `wt0` da Netbird) e as variáveis `ROS_DISCOVERY_SERVER`, `ROS_SUPER_CLIENT`,
  `RMW_IMPLEMENTATION`, `ROS_DOMAIN_ID`.
- A imagem é `ros:humble-ros-base` + `python3-flask` + `python3-pil` + o pacote `sd_msgs` compilado
  com colcon (fornece a mensagem `DirectControl`). Não usa OpenCV do lado do operador (imagens
  comprimidas passam direto; só o raw usa PIL).
- Dentro do container o DNS "twizy" pode não resolver — por isso usamos o IP `100.122.121.134`.

## 3.8 Limitações e pendências conhecidas

- Banda da VPN é o gargalo; acima de ~120 KB/s começa a saturar/instabilizar (P2P × relayed).
- Relays são temporários (não persistem a reboot) — falta integrá-los ao launch/compose do carro.
- Driver do LiDAR (Ouster) pode exigir `docker restart ouster_lidar` após boot (corrida com a rede).
- Para o carro andar, falta selecionar Drive (PRND) — a interface não comanda marcha.
- Bateria/latência exibidas ainda têm partes simuladas; sensores no sidebar são parcialmente estáticos.
