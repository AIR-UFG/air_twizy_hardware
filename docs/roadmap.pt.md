# Status & Roadmap

## O que está funcionando

### Hardware

| Componente | Status |
|------------|--------|
| Renault Twizy 80 (veículo) | Operacional — luz de serviço acesa, manutenção pendente |
| Bateria auxiliar (12V Varley) | Funcional — troca recomendada |
| Bateria de tração | Estado desconhecido — diagnóstico OBD2/CAN necessário |
| StreetDrone XCU | Operacional em `can2` |
| PCAN-GPS FD | IMU funcionando via CAN; GPS não testado ao ar livre |
| Lucid Vision TRI032S-CC | Feed confirmado em ~30 FPS; lente C-mount instalada |
| Ouster LiDAR | Driver operacional; configuração de rede via dnsmasq documentada |
| Teltonika RUT950 | Validado com chip de teste; chip de produção necessário |

### Software

| Componente | Status |
|------------|--------|
| ROS2 Humble + stack Docker | Rodando no PC do veículo |
| FastDDS Discovery Server | Operacional em `twizy:11811` |
| NetBird VPN | Mesh P2P confirmado; hostname `twizy` resolve |
| Interface CAN (`can2`) | Frames recebidos, controle do XCU confirmado |
| Teleop Xbox (`direct_control`) | Funcionando de ponta a ponta via VPN |
| Driver da câmera (arena_camera_ros2) | ~30 FPS, streaming via VPN estável |
| Driver LiDAR (ouster_ros) | Driver inicia; nuvem de pontos publicada |
| Simulação Gazebo | Carrega; teleop por teclado funciona |
| GitHub Pages (docs) | Publicado em [air-ufg.github.io/air_twizy_hardware](https://air-ufg.github.io/air_twizy_hardware) |

---

## Problemas conhecidos

| Problema | Gravidade | Observações |
|----------|-----------|-------------|
| Luz de serviço acesa | Média | Inspeção eletrônica/mecânica necessária antes de uso prolongado |
| Bateria auxiliar envelhecida | Média | +4 anos de uso; histórico de descarga profunda; suporte customizado necessário |
| GPS não testado ao ar livre | Baixa | IMU do PCAN-GPS FD funciona; coordenadas nunca validadas com sinal de satélite |
| `rqt` não funciona via VPN | Baixa | Usar script Python viewer como alternativa |
| Aterramento da tomada do lab | Alta | Tomada de 20A com aterramento correto obrigatória para carregamento |
| Chip SIM do RUT950 | Média | Chip de teste apenas — sem plano de conectividade para produção |
| `can0` / `can1` inutilizáveis | Conhecido | XCU está conectado fisicamente em `can2`; comportamento esperado |

---

## Roadmap

### Curto prazo

- [ ] Trocar bateria auxiliar e fabricar suporte de fixação
- [ ] Adquirir plano de dados para o RUT950
- [ ] Fazer diagnóstico OBD2 para avaliar estado da bateria de tração
- [ ] Testar GPS ao ar livre e validar coordenadas do PCAN-GPS FD
- [ ] Investigar códigos de falha da luz de serviço

### Médio prazo

- [ ] Documentar configuração multi-câmera (segunda unidade Lucid Vision)
- [ ] Validar calibração espacial LiDAR + câmera (extrínseca)
- [ ] Integrar dados de IMU na stack de navegação ROS2
- [ ] Testar latência da teleoperação via 4G (não apenas WiFi/LAN)
- [ ] Substituir tomada do laboratório por tomada de 20A aterrada

### Longo prazo

- [ ] Integrar LiDAR + câmera em pipeline de percepção
- [ ] Implementar frenagem autônoma / desvio de obstáculos
- [ ] Adicionar dashboard de monitoramento remoto (estado do veículo, bateria, rastreamento GPS)
- [ ] Teste de navegação autônoma ao ar livre
- [ ] Documentar versão do firmware do XCU StreetDrone e procedimento de atualização
