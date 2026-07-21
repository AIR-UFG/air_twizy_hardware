#!/usr/bin/env python3
"""
Relay de LiDAR top-down para a VPN (espelha cam_compress_relay.py).

Assina /ouster/points (PointCloud2, ~16 MB/s), projeta em 2D top-down,
filtra por raio, decima para poucas centenas de pontos e publica
/lidar/topdown (std_msgs/Float32MultiArray = [x0,y0,x1,y1,...]) a ~2.5 Hz.
Payload ~2-3 KB por msg -> ~6 KB/s, cabe na VPN de ~0.2 Mbps.

Rodar dentro do container ouster_lidar:
  docker exec -d ouster_lidar bash -lc \
    "source /opt/ros/humble/setup.bash; python3 /tmp/lidar_topdown_relay.py"
"""
import numpy as np
import rclpy
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Float32MultiArray
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

IN_TOPIC  = '/ouster/points'
OUT_TOPIC = '/lidar/topdown'
RADIUS    = 20.0    # m: só pontos dentro deste raio
MIN_R     = 0.8     # m: descarta pontos colados no sensor (carro)
MAX_PTS   = 300     # decima para no máximo isto
RATE      = 2.5     # Hz de publicação

rclpy.init()
node = rclpy.create_node('lidar_topdown_relay')
qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                 durability=DurabilityPolicy.VOLATILE)
pub = node.create_publisher(Float32MultiArray, OUT_TOPIC, qos)
last = [0.0]


def cb(msg: PointCloud2):
    now = node.get_clock().now().nanoseconds / 1e9
    if now - last[0] < 1.0 / RATE:
        return
    last[0] = now
    off = {f.name: f.offset for f in msg.fields}
    if 'x' not in off or 'y' not in off:
        return
    n = msg.width * msg.height
    raw = np.frombuffer(bytes(msg.data), dtype=np.uint8).reshape(n, msg.point_step)
    x = raw[:, off['x']:off['x'] + 4].copy().view(np.float32).ravel()
    y = raw[:, off['y']:off['y'] + 4].copy().view(np.float32).ravel()
    r2 = x * x + y * y
    m = np.isfinite(r2) & (r2 < RADIUS * RADIUS) & (r2 > MIN_R * MIN_R)
    x, y = x[m], y[m]
    if len(x) > MAX_PTS:
        idx = np.random.choice(len(x), MAX_PTS, replace=False)
        x, y = x[idx], y[idx]
    out = np.empty(len(x) * 2, dtype=np.float32)
    out[0::2] = x
    out[1::2] = y
    pub.publish(Float32MultiArray(data=out.tolist()))
    print(f'{len(x)} pts -> {len(out) * 4} bytes', flush=True)


node.create_subscription(PointCloud2, IN_TOPIC, cb, qos)
print(f'lidar relay up: {IN_TOPIC} -> {OUT_TOPIC}', flush=True)
rclpy.spin(node)
