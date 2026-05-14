# Sensores

## PCAN-GPS FD (PEAK System)

O módulo PCAN-GPS FD fornece dados de IMU e GPS via barramento CAN, publicados como tópicos ROS2.

| Especificação | Valor |
|--------------|-------|
| Microcontrolador | NXP LPC4000 series (ARM Cortex-M4) |
| Receptor GNSS | u-blox MAX-7W (GPS, GLONASS, QZSS, SBAS) |
| Acelerômetro + Magnetômetro | Bosch BMC050 (3 eixos cada) |
| Giroscópio | STMicroelectronics L3GD20 (3 eixos) |
| CAN | High-speed CAN (ISO 11898-2), 40 kbit/s a 1 Mbit/s |
| Protocolo CAN | CAN 2.0 A/B |
| Entradas digitais | 2 (High-active) |
| Saída digital | 1 (Low-side driver) |
| Conector | Régua de terminais Phoenix de 10 polos |
| Alimentação | 8 a 30 V DC |
| Armazenamento | Slot microSD (data logging) |
| Temperatura de operação | -40 a +85 °C |

**Resultados dos testes:**

- **IMU:** Acesso aos dados brutos (raw data) realizado com sucesso via barramento CAN e tópicos ROS2
- **GPS:** Coordenadas não obtidas nos testes — testes realizados em ambiente fechado (indoor), sem sinal de satélite

## Lucid Vision TRI032S-CC

| Especificação | Valor |
|--------------|-------|
| Modelo | LUCID Triton TRI032S-CC |
| Serial | 243901923 |
| Sensor | Sony IMX265 CMOS (Global Shutter) |
| Resolução | 3,2 MP (2048 × 1536 px) |
| Taxa de quadros | ~35,4 FPS (base) |
| Interface | GigE Vision (1000BASE-T via conector M12) |
| Tamanho do sensor | 8,9 mm (tipo 1/1,8") |
| Tamanho do pixel | 3,45 µm |
| Montagem de lente | C-Mount |
| Proteção | IP67 (resistente a poeira e água) |
| Alimentação | PoE (Power over Ethernet) ou 12–24 VDC externo |

**Status operacional:**
- Feed rodando em ~30 FPS, visível na mini tela do veículo
- Bug de inicialização multi-câmera (conflito de ID de câmeras) — corrigido
- Transmissão via VPN NetBird: estável; tópicos acessíveis; rqt não funcional via VPN (usar script Python viewer no lugar)

!!! note "Lente"
    A TRI032S-CC não vem com lente. Uma lente C-Mount deve ser instalada. A ausência de lente foi identificada e corrigida durante a configuração inicial.

Veja [Visão Geral da Câmera](../camera/index.md) para detalhes de driver e configuração.

## PC de Bordo

- SO: Ubuntu 22.04 LTS
- Pacotes ROS2 Humble inicializados com sucesso
- Visualização de tópicos confirmada no ROS2
