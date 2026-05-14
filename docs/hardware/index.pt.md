# Hardware do Veículo

## Renault Twizy — Identificação

| Campo | Valor |
|-------|-------|
| Modelo | Renault Twizy 80 |
| Regulamentação EU | L7e-CP e2*168/2013 |
| VIN | VF1ACVYB26037118B9 |
| Ano | 2016 (inferido pelo VIN) |
| Potência nominal | 8,5 kW |
| Velocidade máxima | 80 km/h |
| Carga máxima | 680 kg |

Manual oficial de manutenção: [Renault Xarray Seção 4](https://www.user-manual.renault.com/en/xarray9/section-4-maintenance)

## Sistema Elétrico

### Bateria auxiliar (12V)

A bateria auxiliar de 12V alimenta toda a eletrônica embarcada: PC, sensores, roteador, etc.

| Especificação | Valor |
|--------------|-------|
| Tensão | 12 V |
| Capacidade | 12 Ah ou 14 Ah (original, dependendo da versão) |
| Tipo | Chumbo/Selada AGM (sem eletrólito livre) |
| Unidade atual | Varley Red Top 15 (7065-0005), 12V 15Ah VRLA(AGM) |
| Original | EXIDE 24410 3090R, 12V VRLA(AGM) 14Ah 80A |

!!! warning "Troca da bateria recomendada"
    Fortes indícios de necessidade de troca da bateria auxiliar: envelhecimento (>4 anos), alto volume de ciclagem para alimentar equipamentos de teste, e descarga profunda já reportada. Antes da troca, realizar teste de tensão. Também é necessário fabricar uma fixação pois a unidade Varley atual não se encaixa no suporte original.

**Procedimento seguro de remoção:**

```
Após desligar a ignição → aguardar 35 min → o sistema pode drenar a bateria de
tração para recarregar a auxiliar (para se a tração estiver < 15%). Isolar o
terminal positivo do chassi antes da remoção.
```

### Bateria de tração (lítio, principal)

- O estado de saúde não pode ser lido diretamente — requer scanner OBD2 ou leitura de diagnóstico CAN pelo PC
- Manter o veículo com carga entre 40–60% quando estacionado por períodos prolongados para reduzir degradação acelerada
- Carregar a 100% apenas quando testes de alta quilometragem ou longa duração exigirem

### Carregamento

!!! danger "Aterramento — crítico"
    A tomada do laboratório usada para carregar o veículo deve ter **aterramento correto**. Houve múltiplas falhas no carregador embarcado por falhas de aterramento. É necessária uma **tomada de 20A** — não usar tomadas de 10A (a corrente de carga se aproxima do limite de 10A e má conexão adiciona risco de superaquecimento e incêndio). Atualmente um adaptador genérico está em uso e deve ser substituído.

## Estado Mecânico

| Sistema | Status / Observações |
|---------|---------------------|
| Luz de serviço | ACESA — necessária inspeção eletrônica/mecânica |
| Pneus | Verificar deformações ou rachaduras; calibrar pressão |
| Tamanho dos pneus | Dianteiro e traseiro diferentes — verificar spec antes de comprar |
| Discos de freio | Camada superficial de ferrugem; ciclo de rodagem recomendado |
| Fluido de freio | Troca recomendada; verificar vazamentos embaixo da caixa de direção |
| Fluido da transmissão | Sem necessidade de troca a menos que o veículo ficou parado >2 anos |
| Correia (StreetDrone) | Verificar estado da correia do atuador de freio autônomo |
| Conectores | Inspecionar encaixe correto, sem trincas ou travas quebradas |
| Pontos de aterramento | Testar resistência (deve ser <300 mΩ conforme ISO 6469-3:2011) |
| Bateria de tração | Diagnóstico OBD2 / CAN necessário para avaliar estado de saúde |

## OBD2 / Diagnóstico

O conector OBD2 fica acessível ao retirar a tampa de plástico próxima ao freio de mão. Um scanner automotivo é recomendado para ler códigos de falha antes de encomendar peças de reposição.

Também é possível ler dados de diagnóstico diretamente pelo PC do veículo via porta CAN disponível, mas requer compreensão da estrutura dos dados de diagnóstico (IDs de parâmetros, PIDs) e cuidado para não injetar comandos que possam afetar a segurança do veículo.

Veja [Sensores](sensors.md) para o módulo PCAN-GPS usado para dados de IMU e GPS.
