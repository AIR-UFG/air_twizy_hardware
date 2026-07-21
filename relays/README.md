# Relays de redução (rodam NO CARRO)

A VPN Netbird entrega ~0.2–1 Mbps, mas os dados brutos são enormes (câmera raw ≈ 253 Mbps,
nuvem do LiDAR ≈ 16 MB/s). Estes relays rodam **dentro dos containers do carro**, assinam o
tópico pesado localmente, **reduzem/comprimem** e publicam um tópico pequeno que o dashboard
assina pela VPN. Todos usam QoS BEST_EFFORT e limitam a taxa (fps).

| Script | Container | Assina | Publica |
|---|---|---|---|
| `cam_compress_relay.py` | `air_twizy_camera` | `/camera/<n>/image_raw` (bayer 2048×1536) | `/camera/<n>/image_raw/compressed` (320px, JPEG q40, 3 fps) |
| `lidar_topdown_relay.py` | `ouster_lidar` | `/ouster/points` (PointCloud2) | `/lidar/topdown` (Float32MultiArray, ≤300 pts, 2.5 Hz) |
| `lidar_img_relay.py` | `ouster_lidar` | `/ouster/*_image` (mono16 128×1024) | `/ouster/<n>_image/compressed` (384px, JPEG q30, 0.5 fps) |

## Subir (precisa de acesso SSH ao carro: air@twizy)

Para cada relay: copiar o .py para /tmp do container e rodar detached. Exemplo (lidar img):
```bash
ssh air@twizy 'docker exec -i ouster_lidar bash -c "cat > /tmp/lidar_img_relay.py"' < lidar_img_relay.py
ssh air@twizy 'docker exec -d ouster_lidar bash -lc "source /opt/ros/humble/setup.bash && exec python3 /tmp/lidar_img_relay.py >/tmp/lidar_img_relay.log 2>&1"'
```
Câmera → container `air_twizy_camera`; LiDAR (topdown e img) → container `ouster_lidar`.

**Atenção:** são temporários — NÃO sobrevivem a reboot/recreate dos containers. Idealmente
devem ser integrados ao launch/compose do carro no futuro.

## Ajustes

No topo de cada script: `WIDTH`, `QUALITY`, `RATE` (fps). Reduza se a VPN saturar (>~120 KB/s).
`LIDAR_MAX_R` no `dashboard.py` deve bater com o raio usado no `lidar_topdown_relay.py`.
