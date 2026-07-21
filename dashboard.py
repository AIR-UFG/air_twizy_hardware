#!/usr/bin/env python3
"""
Dashboard de teleoperação Twizy — Flask + ROS 2 (hardware)
Acesse http://localhost:5000 no browser após iniciar.

Controles (teclado no browser):
  W / S      → acelerar / frear
  A / D      → virar esq / dir
  Espaço     → freio de emergência
  I / O      → torque máximo ±10
  K / L      → steer máximo ±5

Uso:
  python3 dashboard.py
  python3 dashboard.py --cam1 /camera_1/image_raw --cam2 /camera_2/image_raw
"""

from __future__ import annotations
import argparse
import io
import threading
import time
import math
import json
import random
import sys

try:
    from flask import Flask, Response, request, jsonify, render_template_string
except ImportError:
    print("Flask não encontrado. Instale com: pip install flask")
    sys.exit(1)

try:
    from PIL import Image as PilImage, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from sensor_msgs.msg import CompressedImage, Image as RosImage
    from std_msgs.msg import Float32MultiArray
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    print("[AVISO] rclpy não encontrado — rodando sem ROS (mock mode)")

try:
    from sd_msgs.msg import DirectControl
    HAS_DIRECT_CONTROL = True
except ImportError:
    HAS_DIRECT_CONTROL = False

# ── parâmetros ────────────────────────────────────────────────────────────────

LOOP_HZ      = 50
DT           = 1.0 / LOOP_HZ
TORQUE_ACCEL = 200.0
TORQUE_COAST = 100.0
TORQUE_BRAKE = 400.0
STEER_RATE   = 150.0
STEER_RETURN = 120.0
DEFAULT_MAX_TORQUE = 30.0
DEFAULT_MAX_STEER  = 100.0

# LiDAR top-down: tópico pequeno vindo do relay do carro (Float32MultiArray [x,y,...])
LIDAR_TOPIC = '/lidar/topdown'
LIDAR_MAX_R = 20.0   # m: raio que mapeia para a borda do canvas (deve bater com o relay)

# LiDAR panoramas (imagens 360° comprimidas pelo relay do carro) — abas do TOP VIEW
LIDAR_IMG_TOPICS = {
    'range':  '/ouster/range_image/compressed',
    'signal': '/ouster/signal_image/compressed',
    'nearir': '/ouster/nearir_image/compressed',
    'reflec': '/ouster/reflec_image/compressed',
}
_lidar_img_frames: dict[str, bytes | None] = {k: None for k in LIDAR_IMG_TOPICS}

# tópicos de câmera por slot (None = offline/placeholder)
# hardware: câmeras Lucid Vision publicam sensor_msgs/Image em /camera_N/image_raw
CAM_TOPICS: dict[int, str | None] = {1: None, 2: None, 3: None, 4: None}
_cam_frames: dict[int, bytes | None] = {1: None, 2: None, 3: None, 4: None}
_cam_lock = threading.Lock()

# ── estado compartilhado ──────────────────────────────────────────────────────

_state = {
    'torque': 0.0,
    'steer': 0.0,
    'max_torque': DEFAULT_MAX_TORQUE,
    'max_steer': DEFAULT_MAX_STEER,
    'emergency': False,
    'keys': set(),
    'battery_pct': 72.0,
    'battery_amp': -1.8,
    'latency_ms': 12,
    'connected': True,
    'sensors': {
        'LIDAR': True, 'GPS': True, 'IMU': True, 'Joystick': False,
        'CAM 1': True, 'CAM 2': False, 'CAM 3': True, 'CAM 4': True, 'RADAR': True,
    },
    'logs': [],
    'lidar': [],   # pontos top-down [[x,y],...] em metros, relativos ao carro
}
_lock = threading.Lock()
_ros_node = None
_last_keys_ts = time.monotonic()

# ── nó ROS ────────────────────────────────────────────────────────────────────

class TeleopNode(Node):  # type: ignore[misc]
    def __init__(self):
        super().__init__('teleop_dashboard')
        if HAS_DIRECT_CONTROL:
            self.pub = self.create_publisher(DirectControl, 'direct_control_cmd', 10)
            _add_log('INFO', 'Publicando em direct_control_cmd (DirectControl)')
        else:
            self.pub = None
            _add_log('WARN', 'sd_msgs não disponível — controle desabilitado')

    def send(self, torque: float, steer: float):
        if self.pub is None:
            return
        msg = DirectControl()
        msg.torque_setpoint = float(torque)
        msg.steer_setpoint  = float(steer)
        self.pub.publish(msg)


class CameraNode(Node):  # type: ignore[misc]
    def __init__(self, slot: int, topic: str):
        super().__init__(f'teleop_cam_{slot}')
        self._slot = slot
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        if topic.endswith('/compressed'):
            self.create_subscription(CompressedImage, topic, self._compressed_cb, qos)
        else:
            self.create_subscription(RosImage, topic, self._raw_cb, qos)
        _add_log('INFO', f'CAM {slot}: assinando {topic}')

    def _compressed_cb(self, msg: CompressedImage):
        with _cam_lock:
            _cam_frames[self._slot] = bytes(msg.data)
        with _lock:
            _state['sensors'][f'CAM {self._slot}'] = True

    def _raw_cb(self, msg: RosImage):
        if not PIL_OK:
            return
        try:
            mode = 'RGB' if msg.encoding in ('rgb8', 'bgr8') else 'L'
            if msg.encoding == 'bgr8':
                img = PilImage.frombytes('RGB', (msg.width, msg.height), bytes(msg.data))
                r, g, b = img.split()
                img = PilImage.merge('RGB', (b, g, r))
            else:
                img = PilImage.frombytes(mode, (msg.width, msg.height), bytes(msg.data))
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=80)
            with _cam_lock:
                _cam_frames[self._slot] = buf.getvalue()
            with _lock:
                _state['sensors'][f'CAM {self._slot}'] = True
        except Exception:
            pass


class LidarNode(Node):  # type: ignore[misc]
    def __init__(self, topic: str):
        super().__init__('teleop_lidar')
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Float32MultiArray, topic, self._cb, qos)
        _add_log('INFO', f'LIDAR: assinando {topic}')

    def _cb(self, msg: Float32MultiArray):
        d = msg.data
        pts = [[round(d[i], 2), round(d[i + 1], 2)] for i in range(0, len(d) - 1, 2)]
        with _lock:
            _state['lidar'] = pts
            _state['sensors']['LIDAR'] = True


class LidarImgNode(Node):  # type: ignore[misc]
    def __init__(self, name: str, topic: str):
        super().__init__(f'teleop_lidarimg_{name}')
        self._name = name
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        self.create_subscription(CompressedImage, topic, self._cb, qos)
        _add_log('INFO', f'LIDAR IMG {name}: assinando {topic}')

    def _cb(self, msg: CompressedImage):
        with _cam_lock:
            _lidar_img_frames[self._name] = bytes(msg.data)


def _ros_thread():
    global _ros_node
    rclpy.init()
    _ros_node = TeleopNode()
    _add_log('INFO', 'ROS 2 iniciado — modo: carro real (DirectControl)')

    cam_nodes = [CameraNode(slot, topic)
                 for slot, topic in CAM_TOPICS.items() if topic]

    executor = MultiThreadedExecutor()
    executor.add_node(_ros_node)
    for n in cam_nodes:
        executor.add_node(n)
    if LIDAR_TOPIC:
        executor.add_node(LidarNode(LIDAR_TOPIC))
    for _n, _t in LIDAR_IMG_TOPICS.items():
        executor.add_node(LidarImgNode(_n, _t))
    executor.spin()

# ── loops de background ───────────────────────────────────────────────────────

def _control_loop():
    while True:
        t0 = time.monotonic()
        with _lock:
            if t0 - _last_keys_ts > 0.5:
                _state['keys'].clear()
            keys      = _state['keys'].copy()
            emergency = _state['emergency'] or 'space' in keys
            mt = _state['max_torque']
            ms = _state['max_steer']

            if emergency:
                _state['torque'] = -mt   # freio: torque negativo máximo (SDControl: -100 = freio máx)
                _state['steer'] *= 0.8
            else:
                torque = _state['torque']
                w = 'w' in keys; s = 's' in keys
                if w and not s:
                    torque = min(mt, torque + TORQUE_ACCEL * DT)
                elif s and not w:
                    torque = max(-mt, torque - TORQUE_BRAKE * DT)
                else:
                    d = TORQUE_COAST * DT
                    torque = 0.0 if abs(torque) <= d else torque - math.copysign(d, torque)
                _state['torque'] = torque

                steer = _state['steer']
                a = 'a' in keys; dd = 'd' in keys
                if a and not dd:
                    steer = min(ms, steer + STEER_RATE * DT)
                elif dd and not a:
                    steer = max(-ms, steer - STEER_RATE * DT)
                else:
                    d = STEER_RETURN * DT
                    steer = 0.0 if abs(steer) <= d else steer - math.copysign(d, steer)
                _state['steer'] = steer

            torque = _state['torque']
            steer  = _state['steer']

        if _ros_node:
            _ros_node.send(torque, steer)

        time.sleep(max(0.0, DT - (time.monotonic() - t0)))

def _mock_loop():
    _add_log('INFO', 'Dashboard iniciado — aguardando conexão do browser')
    _add_log('INFO', 'Publicando em direct_control_cmd (sd_msgs/DirectControl)')
    _add_log('WARN', 'Joystick não detectado em /dev/input/js0')
    while True:
        time.sleep(0.5)
        with _lock:
            _state['battery_pct'] = max(0.0, min(100.0, _state['battery_pct'] + random.uniform(-0.02, 0.01)))
            _state['battery_amp'] = round(-1.8 + random.uniform(-0.15, 0.15), 2)
            _state['latency_ms']  = max(5, min(250, _state['latency_ms'] + random.randint(-3, 4)))
        if random.random() < 0.05:
            _add_log('INFO', f"torque={_state['torque']:.1f}%  steer={_state['steer']:.1f}%")

def _add_log(level: str, msg: str):
    ts = time.strftime('%H:%M:%S')
    entry = {'ts': ts, 'level': level, 'msg': msg}
    with _lock:
        _state['logs'].append(entry)
        if len(_state['logs']) > 200:
            _state['logs'] = _state['logs'][-200:]

# ── Flask ─────────────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route('/')
def index():
    return Response(render_template_string(HTML),
                    headers={'Cache-Control': 'no-store, no-cache, must-revalidate'})

@app.route('/control', methods=['POST'])
def control():
    data = request.json or {}
    action = data.get('action', '')
    global _last_keys_ts
    with _lock:
        if action == 'keys':
            held = {str(k).lower() for k in data.get('held', [])}
            _state['keys'] = held & {'w', 's', 'a', 'd', 'space'}
            _last_keys_ts = time.monotonic()
        elif action == 'keydown':
            _state['keys'].add(str(data.get('key', '')).lower())
            _last_keys_ts = time.monotonic()
        elif action == 'keyup':
            _state['keys'].discard(str(data.get('key', '')).lower())
        elif action == 'emergency':
            active = bool(data.get('active', False))
            _state['emergency'] = active
            if active:
                _state['torque'] = -_state['max_torque']   # freio: torque negativo (não coast)
                _state['steer']  = 0.0
            _add_log('WARN' if active else 'INFO',
                     'FREIO DE EMERGÊNCIA ATIVADO' if active else 'Freio de emergência liberado')
        elif action == 'adjust':
            k = str(data.get('key', '')).lower()
            if k == 'i': _state['max_torque'] = min(100.0, _state['max_torque'] + 10.0)
            elif k == 'o': _state['max_torque'] = max(10.0,  _state['max_torque'] - 10.0)
            elif k == 'k': _state['max_steer']  = min(100.0, _state['max_steer']  + 5.0)
            elif k == 'l': _state['max_steer']  = max(10.0,  _state['max_steer']  - 5.0)
    return jsonify({'ok': True})

@app.route('/stream')
def stream():
    def generate():
        last_log_idx = 0
        while True:
            with _lock:
                snap = {
                    'torque':      round(_state['torque'], 1),
                    'steer':       round(_state['steer'], 1),
                    'max_torque':  _state['max_torque'],
                    'max_steer':   _state['max_steer'],
                    'emergency':   _state['emergency'],
                    'battery_pct': round(_state['battery_pct'], 1),
                    'battery_amp': _state['battery_amp'],
                    'latency_ms':  _state['latency_ms'],
                    'connected':   _state['connected'],
                    'sensors':     dict(_state['sensors']),
                    'lidar':       _state['lidar'],
                    'lidar_max_r': LIDAR_MAX_R,
                    'new_logs':    _state['logs'][last_log_idx:],
                }
                last_log_idx = len(_state['logs'])
            yield f"data: {json.dumps(snap)}\n\n"
            time.sleep(0.1)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

def _no_signal_jpeg() -> bytes:
    if not PIL_OK:
        return b''
    img = PilImage.new('RGB', (320, 240), (11, 11, 24))
    ImageDraw.Draw(img).text((105, 112), 'NO SIGNAL', fill=(60, 60, 85))
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=60)
    return buf.getvalue()

_NO_SIG = None

@app.route('/cam/<int:cam_id>/stream')
def cam_stream(cam_id):
    def generate():
        global _NO_SIG
        if _NO_SIG is None:
            _NO_SIG = _no_signal_jpeg()
        while True:
            with _cam_lock:
                frame = _cam_frames.get(cam_id)
            data = frame if frame else _NO_SIG
            if data:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + data + b'\r\n')
            time.sleep(0.04)
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Cache-Control': 'no-cache'})

@app.route('/lidarimg/<name>.jpg')
def lidarimg_jpg(name):
    global _NO_SIG
    if _NO_SIG is None:
        _NO_SIG = _no_signal_jpeg()
    with _cam_lock:
        frame = _lidar_img_frames.get(name)
    return Response(frame if frame else _NO_SIG, mimetype='image/jpeg',
                    headers={'Cache-Control': 'no-cache'})

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Twizy — Teleop Dashboard</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:    #0b0b18;
    --bg2:   #12121e;
    --bg3:   #1c1c2e;
    --fg:    #d0d0e0;
    --dim:   #5a5a7a;
    --cyan:  #00d4ff;
    --green: #00ff88;
    --red:   #ff3344;
    --amber: #ffaa00;
    --blue:  #4488ff;
    --r: 6px;
  }
  html, body { height: 100%; background: var(--bg); color: var(--fg);
               font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px;
               overflow: hidden; }

  /* ── layout raiz ── */
  .app { display: flex; flex-direction: column; height: 100vh; }

  /* ── topbar ── */
  .topbar {
    display: flex; align-items: center; gap: 12px;
    padding: 0 16px; height: 44px; background: var(--bg2);
    border-bottom: 1px solid #22223a; flex-shrink: 0;
  }
  .latency { display: flex; align-items: center; gap: 6px; color: var(--green); font-weight: 700; }
  .latency .wifi { font-size: 16px; opacity: .8; }
  .badge {
    padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;
    border: 1px solid currentColor;
  }
  .badge.ok  { color: var(--green); }
  .badge.err { color: var(--red); }
  .topbar-bar {
    flex: 1; height: 8px; background: #1a1a2e; border-radius: 4px; overflow: hidden;
    border: 1px solid #22223a;
  }
  .topbar-bar-fill {
    height: 100%; width: 0%;
    transition: width .6s, background-color .8s;
    border-radius: 4px;
    background: var(--green);
  }
  .topbar-bar-fill.charging {
    background: repeating-linear-gradient(
      -45deg, var(--blue) 0, var(--blue) 6px, #2244aa 6px, #2244aa 12px
    ) !important;
    background-size: 200% 100% !important;
    animation: slide 1.2s linear infinite;
  }
  @keyframes slide { to { background-position: -200% 0; } }

  /* ── main ── */
  .main { display: flex; flex: 1; overflow: hidden; }

  /* ── sidebar ── */
  .sidebar {
    width: 180px; flex-shrink: 0; background: var(--bg2);
    border-right: 1px solid #22223a;
    display: flex; flex-direction: column; padding: 12px 10px; gap: 4px; overflow-y: auto;
  }
  .sidebar-section { font-size: 10px; color: var(--dim); text-transform: uppercase;
                     letter-spacing: .08em; margin: 8px 0 4px; }
  .sensor-row { display: flex; align-items: center; gap: 8px; padding: 3px 4px;
                border-radius: 4px; transition: background .15s; cursor: default; }
  .sensor-row:hover { background: #1c1c2e; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .dot.ok  { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .dot.err { background: var(--red);   box-shadow: 0 0 6px var(--red); animation: pulse 1.2s ease-in-out infinite; }
  .dot.dim { background: var(--dim); }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }

  .sidebar-btn {
    margin-top: 6px; padding: 7px 10px; background: var(--bg3);
    border: 1px solid #33334a; border-radius: var(--r); color: var(--fg);
    font-family: inherit; font-size: 12px; cursor: pointer; text-align: left;
    transition: background .15s, border-color .15s;
  }
  .sidebar-btn:hover { background: #22223a; border-color: var(--cyan); color: var(--cyan); }

  /* ── content ── */
  .content { flex: 1; display: flex; flex-direction: column; padding: 10px; gap: 8px;
             overflow: hidden; min-width: 0; }

  /* ── camera grids ── */
  .cam-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; flex-shrink: 0; height: 200px; }
  .cam-panel {
    background: var(--bg2); border: 1px solid #22223a; border-radius: var(--r);
    position: relative; display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .cam-panel::before {
    content: ''; position: absolute; inset: 0;
    background: repeating-linear-gradient(0deg, #0f0f1a 0, #0f0f1a 1px, transparent 1px, transparent 20px),
                repeating-linear-gradient(90deg, #0f0f1a 0, #0f0f1a 1px, transparent 1px, transparent 20px);
  }
  .cam-label {
    position: absolute; top: 8px; left: 10px; font-size: 11px; font-weight: 700;
    color: var(--dim); letter-spacing: .05em;
  }
  .cam-panel.offline { border-color: var(--red); opacity: .7; }
  .cam-signal {
    position: absolute; bottom: 6px; right: 8px; width: 8px; height: 8px;
    border-radius: 50%; background: var(--green); box-shadow: 0 0 6px var(--green);
  }
  .cam-signal.off { background: var(--red); box-shadow: 0 0 6px var(--red); }

  /* ── mid row ── */
  .mid-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; flex-shrink: 0; height: 200px; }

  /* ── controls panel ── */
  .controls-panel {
    background: var(--bg2); border: 1px solid #22223a; border-radius: var(--r);
    padding: 10px; display: flex; flex-direction: column; gap: 8px;
  }
  .ctrl-header { display: flex; align-items: center; gap: 8px; }
  .ctrl-title  { font-size: 11px; font-weight: 700; color: var(--dim); text-transform: uppercase; letter-spacing: .08em; }
  .ps4-icon svg { width: 28px; height: 20px; }

  .vel-row { display: flex; flex-direction: column; gap: 4px; }
  .vel-label { display: flex; justify-content: space-between; font-size: 11px; }
  .vel-label .name { color: var(--dim); }
  .vel-label .val  { font-weight: 700; }
  .vel-track { height: 10px; background: #1a1a2e; border-radius: 5px; position: relative; overflow: hidden; }
  .vel-fill  {
    position: absolute; top: 0; height: 100%; border-radius: 5px;
    transition: width .08s, left .08s;
  }
  .vel-fill.torque-pos { background: var(--green); left: 50%; }
  .vel-fill.torque-neg { background: var(--red);   right: 50%; }
  .vel-fill.steer-pos  { background: var(--cyan);  left: 50%; }
  .vel-fill.steer-neg  { background: var(--cyan);  right: 50%; }
  .vel-center { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: var(--dim); }

  .estop-row {
    margin-top: auto; padding: 6px 0 2px; text-align: center;
    font-size: 10px; color: var(--dim); letter-spacing: .05em;
  }
  .estop-row span { color: var(--amber); font-weight: 700; }
  .estop-indicator {
    height: 28px; border-radius: var(--r); border: 1px solid var(--dim);
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: var(--dim); transition: all .15s;
  }
  .estop-indicator.active { background: var(--red); border-color: var(--red); color: #fff;
                             box-shadow: 0 0 16px var(--red); animation: pulse .4s ease-in-out infinite; }

  /* ── top view (radar) ── */
  .topview-wrap {
    background: var(--bg2); border: 1px solid #22223a; border-radius: var(--r);
    display: flex; flex-direction: column; overflow: hidden;
  }
  .topview-header {
    padding: 6px 10px; display: flex; gap: 10px; align-items: center;
    border-bottom: 1px solid #22223a; flex-shrink: 0;
  }
  .topview-title { font-size: 11px; font-weight: 700; color: var(--dim); text-transform: uppercase; }
  .legend-item   { display: flex; align-items: center; gap: 4px; font-size: 10px; }
  .legend-dot    { width: 8px; height: 8px; border-radius: 50%; }
  .topview-body  { flex: 1; position: relative; overflow: hidden; min-height: 0; }
  #radarCanvas   { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  #lidarPano     { position: absolute; inset: 0; width: 100%; height: 100%;
                   object-fit: fill; background: var(--bg); display: none;
                   image-rendering: pixelated; }
  .lidar-tab     { padding: 2px 7px; border-radius: 4px; border: 1px solid #33334a;
                   background: transparent; color: var(--dim); font-family: inherit;
                   font-size: 10px; font-weight: 700; cursor: pointer; }
  .lidar-tab:hover  { border-color: var(--cyan); color: var(--cyan); }
  .lidar-tab.active { color: var(--cyan); border-color: var(--cyan); background: #16263a; }

  /* ── logs ── */
  .logs-panel {
    flex: 1; min-height: 0; background: var(--bg2); border: 1px solid #22223a;
    border-radius: var(--r); display: flex; flex-direction: column; overflow: hidden;
  }
  .logs-header {
    display: flex; align-items: center; gap: 8px; padding: 6px 12px;
    border-bottom: 1px solid #22223a; flex-shrink: 0;
  }
  .logs-title { font-size: 11px; font-weight: 700; color: var(--dim); text-transform: uppercase;
                letter-spacing: .08em; margin-right: 4px; }
  .logs-filter-input {
    flex: 1; background: var(--bg3); border: 1px solid #33334a; border-radius: 4px;
    color: var(--fg); font-family: inherit; font-size: 11px; padding: 3px 8px;
    max-width: 180px;
  }
  .logs-filter-input:focus { outline: none; border-color: var(--cyan); }
  .log-lvl-btn {
    padding: 2px 8px; border-radius: 4px; border: 1px solid; font-size: 10px; font-weight: 700;
    cursor: pointer; font-family: inherit; transition: opacity .15s;
  }
  .log-lvl-btn.info  { color: var(--fg);    border-color: var(--dim);   background: transparent; }
  .log-lvl-btn.warn  { color: var(--amber); border-color: var(--amber); background: transparent; }
  .log-lvl-btn.err   { color: var(--red);   border-color: var(--red);   background: transparent; }
  .log-lvl-btn.off   { opacity: .35; }
  .logs-body {
    flex: 1; overflow-y: auto; padding: 6px 12px; font-size: 11px;
    scrollbar-width: thin; scrollbar-color: #33334a transparent;
  }
  .log-entry { display: flex; gap: 8px; padding: 2px 0; border-bottom: 1px solid #1a1a2a; }
  .log-ts    { color: var(--dim); flex-shrink: 0; }
  .log-lvl   { flex-shrink: 0; font-weight: 700; width: 36px; }
  .log-lvl.INFO { color: var(--fg); }
  .log-lvl.WARN { color: var(--amber); }
  .log-lvl.ERR  { color: var(--red); }
  .log-msg   { color: var(--fg); }

  /* ── emergency overlay ── */
  .emergency-overlay {
    position: fixed; inset: 0; background: rgba(255,51,68,.08);
    border: 3px solid var(--red); pointer-events: none;
    opacity: 0; z-index: 100;
  }
  .emergency-overlay.active { animation: emergency-flash .4s ease-in-out infinite; }
  @keyframes emergency-flash { 0%,100% { opacity: .6; } 50% { opacity: .1; } }

  /* ── scrollbar ── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #33334a; border-radius: 3px; }
</style>
</head>
<body>
<div class="emergency-overlay" id="emergencyOverlay"></div>

<div class="app">
  <!-- ── TOPBAR ── -->
  <header class="topbar">
    <div class="latency">
      <span id="latencyVal">—</span><span>ms</span>
      <span class="wifi">&#x29BE;</span>
    </div>
    <span class="badge ok" id="connBadge">Connected</span>
    <div class="topbar-bar"><div class="topbar-bar-fill" id="topBarFill"></div></div>
    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
      <span style="font-size:11px;color:var(--dim)">BAT</span>
      <span id="topBatPct" style="font-size:13px;font-weight:700;color:var(--green)">72%</span>
      <span id="topBatAmp" style="font-size:12px;color:var(--red)">-1.80A</span>
    </div>
    <span style="font-size:11px;color:var(--dim)">SD Twizy Teleop</span>
  </header>

  <div class="main">
    <!-- ── SIDEBAR ── -->
    <nav class="sidebar">
      <div class="sidebar-section">Sensores</div>
      <div class="sensor-row"><div class="dot ok" id="dot-LIDAR"></div><span>LIDAR</span></div>
      <div class="sensor-row"><div class="dot ok" id="dot-GPS"></div><span>GPS</span></div>
      <div class="sensor-row"><div class="dot ok" id="dot-IMU"></div><span>IMU</span></div>
      <div class="sensor-row"><div class="dot err" id="dot-Joystick"></div><span>Joystick</span></div>

      <div class="sidebar-section">Câmeras</div>
      <div class="sensor-row"><div class="dot ok"  id="dot-CAM 1"></div><span>CAM 1</span></div>
      <div class="sensor-row"><div class="dot err" id="dot-CAM 2"></div><span>CAM 2</span></div>
      <div class="sensor-row"><div class="dot ok"  id="dot-CAM 3"></div><span>CAM 3</span></div>
      <div class="sensor-row"><div class="dot ok"  id="dot-CAM 4"></div><span>CAM 4</span></div>
      <div class="sensor-row"><div class="dot ok"  id="dot-RADAR"></div><span>RADAR</span></div>

      <button class="sidebar-btn" onclick="toggleDiag()">&#x2699; Diagnostics</button>
      <button class="sidebar-btn" onclick="toggleSettings()">&#x2630; Settings</button>
    </nav>

    <!-- ── CONTENT ── -->
    <div class="content">

      <!-- Câmeras superiores -->
      <div class="cam-row">
        <div class="cam-panel" id="cam1">
          <div class="cam-label">CAM 1</div>
          <img src="/cam/1/stream" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;">
          <div class="cam-signal" id="sig-cam1" style="z-index:2"></div>
        </div>
        <div class="cam-panel" id="cam2">
          <div class="cam-label">CAM 2</div>
          <img src="/cam/2/stream" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;">
          <div class="cam-signal" id="sig-cam2" style="z-index:2"></div>
        </div>
        <div class="cam-panel" id="cam3">
          <div class="cam-label">CAM 3</div>
          <img src="/cam/3/stream" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;">
          <div class="cam-signal" id="sig-cam3" style="z-index:2"></div>
        </div>
      </div>

      <!-- Linha de controles / CAM4 / Top View -->
      <div class="mid-row">
        <!-- Controles -->
        <div class="controls-panel">
          <div class="ctrl-header">
            <div class="ps4-icon">
              <svg viewBox="0 0 48 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 8 C6 8 2 14 2 20 L6 28 L10 24 L10 18 L14 18 L14 28 L18 28 L18 8 Z" fill="#5a5a7a"/>
                <path d="M36 8 C42 8 46 14 46 20 L42 28 L38 24 L38 18 L34 18 L34 28 L30 28 L30 8 Z" fill="#5a5a7a"/>
                <rect x="18" y="8" width="12" height="20" rx="2" fill="#44445a"/>
                <circle cx="20" cy="14" r="2" fill="#00d4ff" opacity=".7"/>
                <circle cx="28" cy="14" r="2" fill="#ff3344" opacity=".7"/>
                <circle cx="24" cy="11" r="2" fill="#aaaacc" opacity=".5"/>
                <circle cx="24" cy="17" r="2" fill="#aaaacc" opacity=".5"/>
              </svg>
            </div>
            <span class="ctrl-title">Controles</span>
          </div>

          <div class="vel-row">
            <div class="vel-label">
              <span class="name">Vel Lin</span>
              <span class="val" id="torqueVal" style="color:var(--green)">+0.0%</span>
            </div>
            <div class="vel-track">
              <div class="vel-center"></div>
              <div class="vel-fill torque-pos" id="torqueFillPos" style="width:0%"></div>
              <div class="vel-fill torque-neg" id="torqueFillNeg" style="width:0%"></div>
            </div>
          </div>

          <div class="vel-row">
            <div class="vel-label">
              <span class="name">Vel Ang</span>
              <span class="val" id="steerVal" style="color:var(--cyan)">+0.0%</span>
            </div>
            <div class="vel-track">
              <div class="vel-center"></div>
              <div class="vel-fill steer-pos" id="steerFillPos" style="width:0%"></div>
              <div class="vel-fill steer-neg" id="steerFillNeg" style="width:0%"></div>
            </div>
          </div>

          <div class="estop-row">
            <span>ESPAÇO</span> = freio emergência
          </div>
          <div class="estop-indicator" id="estopInd">PRONTO</div>
        </div>

        <!-- CAM 4 -->
        <div class="cam-panel" id="cam4">
          <div class="cam-label">CAM 4</div>
          <img src="/cam/4/stream" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;">
          <div class="cam-signal" id="sig-cam4" style="z-index:2"></div>
        </div>

        <!-- Top View / LiDAR (abas) -->
        <div class="topview-wrap">
          <div class="topview-header">
            <button class="lidar-tab active" data-tab="cloud"  onclick="setLidarTab('cloud')">Nuvem</button>
            <button class="lidar-tab"        data-tab="range"  onclick="setLidarTab('range')">Range</button>
            <button class="lidar-tab"        data-tab="signal" onclick="setLidarTab('signal')">Signal</button>
            <button class="lidar-tab"        data-tab="nearir" onclick="setLidarTab('nearir')">Near-IR</button>
            <button class="lidar-tab"        data-tab="reflec" onclick="setLidarTab('reflec')">Reflec</button>
          </div>
          <div class="topview-body">
            <canvas id="radarCanvas"></canvas>
            <img id="lidarPano" alt="">
          </div>
        </div>
      </div>

      <!-- Logs -->
      <div class="logs-panel">
        <div class="logs-header">
          <span class="logs-title">ROS Logs</span>
          <input class="logs-filter-input" id="logFilter" placeholder="filtrar..." oninput="filterLogs()">
          <button class="log-lvl-btn info"  id="btn-INFO" onclick="toggleLevel('INFO')">INFO</button>
          <button class="log-lvl-btn warn"  id="btn-WARN" onclick="toggleLevel('WARN')">WARN</button>
          <button class="log-lvl-btn err"   id="btn-ERR"  onclick="toggleLevel('ERR')">ERR</button>
        </div>
        <div class="logs-body" id="logsBody"></div>
      </div>
    </div>
  </div>
</div>

<script>
// ── estado ────────────────────────────────────────────────────────────────────
const levels     = { INFO: true, WARN: true, ERR: true };
const heldKeys   = new Set();
let   emergency  = false;
let   adjustCool = {};
let   allLogs    = [];

// ── radar canvas ──────────────────────────────────────────────────────────────
const canvas = document.getElementById('radarCanvas');
const ctx    = canvas.getContext('2d');
let   lidarPts  = [];    // [[x,y],...] em metros (x=frente, y=esquerda)
let   lidarMaxR = 20.0;  // metros no anel externo

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width  = rect.width;
  canvas.height = rect.height;
}

let lidarTab = 'cloud';
let lidarTimer = null;
function refreshPano() {
  if (lidarTab === 'cloud') return;
  document.getElementById('lidarPano').src = '/lidarimg/' + lidarTab + '.jpg?t=' + Date.now();
}
function setLidarTab(name) {
  lidarTab = name;
  document.querySelectorAll('.lidar-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === name));
  const cv = document.getElementById('radarCanvas');
  const im = document.getElementById('lidarPano');
  if (lidarTimer) { clearInterval(lidarTimer); lidarTimer = null; }
  if (name === 'cloud') {
    cv.style.display = 'block';
    im.style.display = 'none';
    im.src = '';
  } else {
    cv.style.display = 'none';
    im.style.display = 'block';
    refreshPano();
    lidarTimer = setInterval(refreshPano, 1000);   // JPEG único a cada 1s (sem MJPEG persistente)
  }
}

function drawRadar() {
  resizeCanvas();
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2;
  const maxR = Math.min(W, H) * 0.44;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0b0b18';
  ctx.fillRect(0, 0, W, H);

  for (let i = 1; i <= 4; i++) {
    const r = maxR * (i / 4);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255,51,68,${0.08 + i * 0.04})`;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // pontos do LiDAR (top-down): x=frente->cima, y=esquerda->esquerda
  const scale = maxR / lidarMaxR;
  ctx.fillStyle = 'rgba(255,51,68,0.85)';
  for (let i = 0; i < lidarPts.length; i++) {
    const px = cx - lidarPts[i][1] * scale;
    const py = cy - lidarPts[i][0] * scale;
    ctx.fillRect(px - 1, py - 1, 2, 2);
  }

  ctx.beginPath();
  ctx.arc(cx, cy, 3, 0, Math.PI * 2);
  ctx.fillStyle = '#00d4ff';
  ctx.fill();

  requestAnimationFrame(drawRadar);
}
drawRadar();

// ── SSE stream ────────────────────────────────────────────────────────────────
const sse = new EventSource('/stream');
sse.onmessage = e => {
  const d = JSON.parse(e.data);

  document.getElementById('latencyVal').textContent = d.latency_ms;

  const fill = document.getElementById('topBarFill');
  fill.style.width = d.battery_pct + '%';
  const charging = d.battery_amp > 0;
  if (charging) {
    fill.className = 'topbar-bar-fill charging';
    fill.style.backgroundColor = '';
  } else {
    fill.className = 'topbar-bar-fill';
    const hue = Math.round(d.battery_pct * 1.2);
    fill.style.backgroundColor = `hsl(${hue}, 100%, 45%)`;
  }

  const badge = document.getElementById('connBadge');
  badge.textContent = d.connected ? 'Connected' : 'Disconnected';
  badge.className   = 'badge ' + (d.connected ? 'ok' : 'err');

  const bp = d.battery_pct;
  const bfColor = bp < 20 ? 'var(--red)' : bp < 50 ? 'var(--amber)' : 'var(--green)';
  document.getElementById('topBatPct').textContent = bp.toFixed(1) + '%';
  document.getElementById('topBatPct').style.color = bfColor;
  document.getElementById('topBatAmp').textContent = d.battery_amp.toFixed(2) + 'A';

  for (const [name, ok] of Object.entries(d.sensors)) {
    const dot = document.getElementById('dot-' + name);
    if (dot) dot.className = 'dot ' + (ok ? 'ok' : 'err');
  }

  const mt = d.max_torque, ms = d.max_steer;
  const tp = (d.torque / mt) * 50, sp = (d.steer / ms) * 50;
  document.getElementById('torqueVal').textContent = (d.torque >= 0 ? '+' : '') + d.torque.toFixed(1) + '%';
  document.getElementById('torqueVal').style.color = d.torque < -0.5 ? 'var(--red)' : d.torque > 0.5 ? 'var(--green)' : 'var(--dim)';
  document.getElementById('torqueFillPos').style.width = (tp > 0 ? tp : 0) + '%';
  document.getElementById('torqueFillNeg').style.width = (tp < 0 ? -tp : 0) + '%';
  document.getElementById('steerVal').textContent = (d.steer >= 0 ? '+' : '') + d.steer.toFixed(1) + '%';
  document.getElementById('steerFillPos').style.width = (sp > 0 ? sp : 0) + '%';
  document.getElementById('steerFillNeg').style.width = (sp < 0 ? -sp : 0) + '%';

  const estop = document.getElementById('estopInd');
  const overlay = document.getElementById('emergencyOverlay');
  if (d.emergency) {
    estop.textContent = '⚠ FREIO DE EMERGÊNCIA';
    estop.classList.add('active');
    overlay.classList.add('active');
  } else {
    estop.textContent = 'PRONTO';
    estop.classList.remove('active');
    overlay.classList.remove('active');
  }

  if (d.lidar) lidarPts = d.lidar;
  if (d.lidar_max_r) lidarMaxR = d.lidar_max_r;

  if (d.new_logs && d.new_logs.length) {
    d.new_logs.forEach(appendLog);
  }
};
sse.onerror = () => {
  document.getElementById('connBadge').textContent = 'Reconnecting...';
  document.getElementById('connBadge').className = 'badge err';
};

// ── logs ──────────────────────────────────────────────────────────────────────
function appendLog(entry) {
  allLogs.push(entry);
  if (allLogs.length > 500) allLogs.shift();
  if (!levels[entry.level]) return;
  const filter = document.getElementById('logFilter').value.toLowerCase();
  if (filter && !entry.msg.toLowerCase().includes(filter)) return;
  const body = document.getElementById('logsBody');
  const row  = document.createElement('div');
  row.className = 'log-entry';
  row.innerHTML =
    `<span class="log-ts">${entry.ts}</span>` +
    `<span class="log-lvl ${entry.level}">${entry.level}</span>` +
    `<span class="log-msg">${escHtml(entry.msg)}</span>`;
  body.appendChild(row);
  body.scrollTop = body.scrollHeight;
  if (body.children.length > 300) body.removeChild(body.firstChild);
}

function filterLogs() {
  const filter = document.getElementById('logFilter').value.toLowerCase();
  const body   = document.getElementById('logsBody');
  body.innerHTML = '';
  for (const e of allLogs) {
    if (!levels[e.level]) continue;
    if (filter && !e.msg.toLowerCase().includes(filter)) continue;
    const row = document.createElement('div');
    row.className = 'log-entry';
    row.innerHTML =
      `<span class="log-ts">${e.ts}</span>` +
      `<span class="log-lvl ${e.level}">${e.level}</span>` +
      `<span class="log-msg">${escHtml(e.msg)}</span>`;
    body.appendChild(row);
  }
  body.scrollTop = body.scrollHeight;
}

function toggleLevel(lvl) {
  levels[lvl] = !levels[lvl];
  document.getElementById('btn-' + lvl).classList.toggle('off', !levels[lvl]);
  filterLogs();
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── teclado ───────────────────────────────────────────────────────────────────
const CONTROL_KEYS = new Set(['w','s','a','d']);
const ADJUST_KEYS  = new Set(['i','o','k','l']);

const CONTROL_SEND_MS = 150;   // throttle do envio de controle (era 100 = 10Hz)
let   _lastHeldSig = '';
function sendKeys() {
  const sig = [...heldKeys].sort().join(',');
  if (heldKeys.size === 0 && sig === _lastHeldSig) return;  // parado: não floodar o servidor
  _lastHeldSig = sig;
  post('/control', { action: 'keys', held: [...heldKeys] });
}

setInterval(sendKeys, CONTROL_SEND_MS);

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  const key = e.key.toLowerCase() === ' ' ? 'space' : e.key.toLowerCase();
  if (e.repeat) return;

  if (key === 'space') {
    e.preventDefault();
    setEmergency(true);
    return;
  }
  if (ADJUST_KEYS.has(key)) {
    const now = Date.now();
    if (!adjustCool[key] || now - adjustCool[key] >= 250) {
      adjustCool[key] = now;
      post('/control', { action: 'adjust', key });
    }
    return;
  }
  if (CONTROL_KEYS.has(key)) {
    heldKeys.add(key);
    sendKeys();
  }
});

document.addEventListener('keyup', e => {
  if (e.target.tagName === 'INPUT') return;
  const key = e.key.toLowerCase() === ' ' ? 'space' : e.key.toLowerCase();
  if (key === 'space') {
    setEmergency(false);
    return;
  }
  if (CONTROL_KEYS.has(key)) {
    heldKeys.delete(key);
    sendKeys();
  }
});

window.addEventListener('blur', () => {
  heldKeys.clear();
  sendKeys();
});

function setEmergency(active) {
  if (emergency === active) return;
  emergency = active;
  post('/control', { action: 'emergency', active });
}

function post(url, data) {
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    .catch(() => {});
}

function toggleDiag() { alert('Diagnostics — em breve'); }
function toggleSettings() { alert('Settings — em breve'); }
</script>
</body>
</html>"""

# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Twizy Teleop Dashboard (hardware)')
    parser.add_argument('--cam1', default='/camera_1/image_raw', metavar='TOPIC',
                        help='Tópico Image para CAM 1 (padrão: /camera_1/image_raw)')
    parser.add_argument('--cam2', default='/camera_2/image_raw', metavar='TOPIC',
                        help='Tópico Image para CAM 2 (padrão: /camera_2/image_raw)')
    parser.add_argument('--cam3', default=None, metavar='TOPIC',
                        help='Tópico Image para CAM 3 (opcional)')
    parser.add_argument('--cam4', default=None, metavar='TOPIC',
                        help='Tópico Image para CAM 4 (opcional)')
    parser.add_argument('--lidar', default=LIDAR_TOPIC, metavar='TOPIC',
                        help=f'Tópico Float32MultiArray top-down do LiDAR (padrão: {LIDAR_TOPIC})')
    args = parser.parse_args()

    LIDAR_TOPIC = args.lidar

    for slot, val in [(1, args.cam1), (2, args.cam2), (3, args.cam3), (4, args.cam4)]:
        if val:
            CAM_TOPICS[slot] = val

    if ROS_AVAILABLE:
        threading.Thread(target=_ros_thread, daemon=True).start()
        time.sleep(0.5)
    else:
        _add_log('WARN', 'ROS não disponível — rodando em mock mode')

    threading.Thread(target=_control_loop, daemon=True).start()
    threading.Thread(target=_mock_loop,    daemon=True).start()

    print("Dashboard disponível em: http://localhost:5000")
    print("Pressione Ctrl+C para encerrar.")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
