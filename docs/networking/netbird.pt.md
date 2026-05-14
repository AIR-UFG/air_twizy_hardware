# Configuração do NetBird VPN

O NetBird cria uma VPN mesh criptografada entre todos os dispositivos da equipe. Cada máquina recebe um hostname e IP estáveis na rede NetBird, independentemente da rede física ou NAT.

## Por que NetBird

- Não precisa de IP estático no veículo — o RUT950 tem IP 4G dinâmico
- Peer-to-peer quando possível (baixa latência), fallback via relay quando o NAT bloqueia conexão direta
- Funciona sobre 4G, WiFi e qualquer conexão à internet
- Plano gratuito disponível para equipes pequenas (self-hosted ou nuvem)

## Instalação (todas as máquinas)

```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sh
```

## Autenticação e conexão

```bash
# Gere um token de autenticação no dashboard do NetBird (nuvem ou self-hosted)
# depois conecte:
sudo netbird up --setup-key <token_gerado>
```

## Verificação

```bash
# Listar peers conectados e seu status
netbird status

# Tanto o veículo quanto o laptop do operador devem aparecer como "Connected"
# Exemplo de saída:
# Peers:
#  twizy-pc                Connected, IP: 100.X.X.1
#  operator-laptop         Connected, IP: 100.X.X.2

# Testar acessibilidade
ping <hostname_netbird_veiculo>
```

## Considerações de rede para ROS2

Os containers Docker do ROS2 devem usar `network_mode: host` para que o tráfego ROS2 seja roteado pela interface NetBird (`wt0`) em vez de ficar isolado dentro da rede bridge do Docker.

```yaml
# trecho do docker-compose.yml
services:
  carro:
    network_mode: host   # obrigatório — roteia ROS2 pela wt0 do NetBird
```

!!! warning "Conflito com interface GigE da câmera"
    O FastDDS Discovery Server deve ser configurado para escutar apenas na interface NetBird (`wt0`), **não** na interface GigE da câmera (`169.254.x.x`). Executar o servidor em todas as interfaces causou conflito que impedia a conexão da câmera. Veja [Discovery Server](discovery-server.md) para a configuração correta.

## Verificar a interface NetBird

```bash
ip addr show wt0
# Deve mostrar um endereço 100.x.x.x ou similar atribuído pelo NetBird
```
