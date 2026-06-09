# Rodar a interface de teleoperação no seu PC (do zero)

Guia para quem **não tem nada instalado** e quer rodar o dashboard web de
teleoperação do Twizy, nos dois modos:

- **Modo A — com simulação:** tudo no seu PC, sem carro e sem VPN. Gazebo faz o
  papel do carro.
- **Modo B — sem simulação:** conecta no **carro real** pela VPN Netbird.

A interface é a mesma nos dois modos. Só muda **onde** ela busca o ROS.

---

## 1. Pré-requisitos (instalar uma vez)

| O quê | Para quê | Modo A | Modo B |
|---|---|:---:|:---:|
| Linux (Ubuntu 22.04 recomendado) | Base de tudo | ✅ | ✅ |
| Docker Engine + plugin Compose | Roda tudo em container | ✅ | ✅ |
| git | Baixar o código | ✅ | ✅ |
| Navegador (Chrome/Firefox) | Abrir o dashboard | ✅ | ✅ |
| Sessão gráfica (X11) | Ver a janela do Gazebo | ✅ | — |
| Cliente Netbird + acesso à rede do time | Achar o carro (`twizy`) | — | ✅ |

> Você **não** precisa instalar ROS, Python, Flask nem nada disso no PC. Tudo
> roda dentro do Docker.

### 1.1 Instalar Docker + Compose (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) \
signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# rodar docker sem sudo (relogar depois)
sudo usermod -aG docker $USER
```

Sair e entrar de novo na sessão, depois testar:

```bash
docker run --rm hello-world
```

### 1.2 Baixar o projeto do dashboard

```bash
git clone --recursive <URL_DESTE_PROJETO> twizy
cd twizy
```

> O `--recursive` é obrigatório: o código da simulação e do `sd_msgs` vem em
> submódulos. Se esquecer: `git submodule update --init --recursive`.

### 1.3 Construir a imagem do dashboard (vale para os dois modos)

```bash
cp env.exemple .env      # só para o compose não reclamar
docker compose build dashboard
```

Isso gera a imagem `air-twizy-dashboard:latest`. É a **mesma** imagem usada nos
dois modos.

---

## 2. Modo A — com simulação (tudo local, sem carro)

São dois processos rodando ao mesmo tempo no seu PC:

```
   Gazebo (carro simulado)            Dashboard
   assina direct_control_cmd   ◀────  publica direct_control_cmd
   publica sensores                   mostra câmeras / telemetria
        └──────── ROS 2 local (DDS multicast, mesma máquina) ────────┘
```

### 2.1 Subir a simulação (terminal 1)

A simulação está no submódulo `workspace/twizy` (repo `air_twizy_simulation`).

```bash
cd workspace/twizy
./utils/build_docker.sh          # primeira vez: baixa Gazebo, demora
./utils/run.sh GPU=false         # use GPU=true se tiver placa NVIDIA
```

Quando a janela do Gazebo abrir, **aperte play**. O `INTERFACE=true` (default
no `.env` da simulação) já sobe o vehicle interface, que é quem escuta os
comandos do dashboard.

> Detalhes e parâmetros da simulação: `workspace/twizy/README.md`.

### 2.2 Subir o dashboard (terminal 2)

Aqui **não** use `docker compose up dashboard` — o compose força o endereço do
carro real (`twizy:11811`). Para falar com a simulação local, rode a imagem
**sem** discovery server:

```bash
cd ~/twizy        # raiz do projeto
docker run --rm --network host \
    -v "$PWD/dashboard.py:/root/dashboard.py:ro" \
    air-twizy-dashboard:latest
```

Abra **http://localhost:5000** no navegador. Clique na página e dirija o carro
simulado pelo teclado (controles na seção 4).

> **Câmeras:** dependem do que a simulação publica. Se aparecer "NO SIGNAL",
> liste os tópicos e ajuste:
> ```bash
> docker run --rm --network host air-twizy-dashboard:latest \
>     bash -lc "source /opt/ros/humble/setup.bash; ros2 topic list | grep -i image"
> ```
> Depois rode o dashboard apontando para o tópico certo, ex.:
> ```bash
> docker run --rm --network host -v "$PWD/dashboard.py:/root/dashboard.py:ro" \
>     air-twizy-dashboard:latest \
>     python3 /root/dashboard.py --cam1 /camera/image_raw
> ```

---

## 3. Modo B — sem simulação (carro real)

```
   PC DO CARRO (twizy)              SEU PC
   stack ROS rodando      ◀─Netbird─  dashboard
```

### 3.1 Entrar na VPN

Instale o cliente Netbird, entre na rede do time e confirme que enxerga o carro:

```bash
ping twizy
```

Se `twizy` não resolver, adicione o IP Netbird do carro no `/etc/hosts`.

### 3.2 Subir o dashboard

O carro precisa estar com o stack no ar **antes** (câmeras, vehicle interface,
discovery server). Com isso pronto:

```bash
cd ~/twizy
docker compose up dashboard
```

Abra **http://localhost:5000**. O compose já aponta para `twizy:11811` via
Netbird.

> Mais detalhes do lado do carro e da arquitetura: `GUIA_TELEOPERACAO.md`.

---

## 4. Controles (teclado, com a aba do navegador em foco)

| Tecla | Ação |
|---|---|
| W / S | Acelerar / frear |
| A / D | Virar esquerda / direita |
| Espaço | Freio de emergência (zera tudo) |
| I / O | Torque máximo ±10 |
| K / L | Steer máximo ±5 |

Segurança: soltou a tecla → torque volta a zero; perdeu o foco da aba → tudo é
zerado.

---

## 5. Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `docker: permission denied` | Faltou relogar após `usermod -aG docker` |
| Dashboard abre mas nada se move (sim) | Não apertou **play** no Gazebo, ou a sim subiu sem `INTERFACE=true` |
| Dashboard não acha o carro (modo B) | Netbird caiu (`ping twizy`) ou stack do carro não está no ar |
| Câmeras "NO SIGNAL" | Tópico de imagem com outro nome — veja a nota da seção 2.2 |
| Controle não responde | Aba do navegador sem foco — clique na página |
| Porta 5000 ocupada | Já tem outro dashboard rodando; feche-o antes |

---

## 6. Resumo de comandos

**Setup (uma vez):**
```bash
git clone --recursive <URL> twizy && cd twizy
cp env.exemple .env
docker compose build dashboard
```

**Modo A (simulação):**
```bash
# terminal 1
cd workspace/twizy && ./utils/build_docker.sh && ./utils/run.sh GPU=false
# terminal 2
docker run --rm --network host -v "$PWD/dashboard.py:/root/dashboard.py:ro" \
    air-twizy-dashboard:latest
```

**Modo B (carro real):**
```bash
ping twizy            # Netbird ativa
docker compose up dashboard
```

Em ambos: abrir **http://localhost:5000**.
