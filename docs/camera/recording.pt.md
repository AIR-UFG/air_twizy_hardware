# Gravação

## MP4 Direto (recomendado)

Grava vídeo diretamente do tópico da câmera sem arquivos intermediários:

```bash
python3 /arena_camera_ros2/scripts/record_video.py --output camera.mp4
# Pressione Ctrl+C para parar e finalizar o arquivo
```

## Bag ROS2 (sem perdas, para pós-processamento)

```bash
cd /arena_camera_ros2/bags
ros2 bag record /camera/image_raw -s mcap
```

A bag é armazenada em `workspace/camera-lucid/bags/` no host (volume montado).

## Converter bag para MP4

```bash
# Usando o wrapper de um comando
python3 /arena_camera_ros2/scripts/convert_bag.py ./minha_bag --output video.mp4

# Ou o script de mais baixo nível
python3 /arena_camera_ros2/scripts/bag_to_video.py --bag ./minha_bag --output video.mp4
```

## Gravar somente o stream comprimido

Se o relay de compressão estiver rodando, grave o tópico comprimido para arquivos menores:

```bash
ros2 bag record /camera/image_raw/compressed -s mcap -o bag_comprimida
```
