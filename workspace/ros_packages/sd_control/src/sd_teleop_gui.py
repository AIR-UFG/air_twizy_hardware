#!/usr/bin/env python3
"""
GUI teleop para air_twizy_simulation.
Tkinter detecta key-press e key-release reais — sem limitação de teclas simultâneas.
Publica AckermannDriveStamped em /sd_control/cmd_vel.
"""

from __future__ import annotations
import threading
import time
import sys
import tkinter as tk

import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped

# ── parâmetros ────────────────────────────────────────────────────────────────

LOOP_MS    = 20       # 50 Hz — física e GUI
PUB_EVERY  = 3        # publicar a cada 3 ticks → ~17 Hz (próximo dos 20 Hz do PS4)

SPEED_ACCEL  = 4.0    # (rad/s)/s — segurar W
SPEED_COAST  = 2.0    # (rad/s)/s — rolagem
SPEED_BRAKE  = 8.0    # (rad/s)/s — segurar S
STEER_RATE   = 1.5    # rad/s    — segurar A/D
STEER_RETURN = 1.2    # rad/s    — retorno ao centro

DEFAULT_MAX_SPEED = 5.0
DEFAULT_MAX_STEER = 0.45
STEP_SPEED        = 1.0
STEP_STEER        = 0.05
MIN_SPEED, MAX_SPEED       = 1.0, 10.0
MIN_STEER, MAX_STEER_CAP   = 0.10, 0.48  # margem antes do limite físico da junta (0.52 rad)
ADJUST_COOLDOWN = 0.25

DT = LOOP_MS / 1000.0

# ── cores ─────────────────────────────────────────────────────────────────────

BG      = '#12121e'
BG2     = '#1c1c2e'
FG      = '#e0e0e0'
CYAN    = '#00d4ff'
GREEN   = '#00ff88'
RED     = '#ff4455'
YELLOW  = '#ffd700'
GREY    = '#555566'


# ── nó ROS ───────────────────────────────────────────────────────────────────

class TeleopNode(Node):
    def __init__(self) -> None:
        super().__init__('teleop_gui')
        self.pub = self.create_publisher(
            AckermannDriveStamped, '/sd_control/cmd_vel', 10)

    def send(self, speed: float, steer: float) -> None:
        msg = AckermannDriveStamped()
        msg.header.stamp         = self.get_clock().now().to_msg()
        msg.drive.speed          = speed
        msg.drive.steering_angle = steer
        self.pub.publish(msg)


# ── GUI ───────────────────────────────────────────────────────────────────────

class TeleopGUI:
    def __init__(self, node: TeleopNode) -> None:
        self.node = node

        self._speed     = 0.0
        self._steer     = 0.0
        self._max_speed = DEFAULT_MAX_SPEED
        self._max_steer = DEFAULT_MAX_STEER

        # Teclas atualmente pressionadas (keysym.lower())
        self._held: set[str] = set()

        # Temporizadores de remoção com delay para filtrar o key-repeat do X11,
        # que envia KeyRelease+KeyPress falsos entre cada repeat.
        self._rel_timers: dict[str, str] = {}
        self._adj_last:   dict[str, float] = {}

        self._pub_tick = 0   # contador para limitar publicação ROS a ~17 Hz

        self._build()

    # ── construção da janela ──────────────────────────────────────────────────

    def _build(self) -> None:
        self.root = tk.Tk()
        self.root.title('SD Twizy — Teleop')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        pad = dict(padx=14, pady=4)

        # título
        tk.Label(self.root, text='SD Twizy Teleop', bg=BG,
                 fg=CYAN, font=('Monospace', 15, 'bold')).pack(pady=(12, 0))

        # legenda
        leg = ('W / S  →  Acelerar / Frear          Espaço  →  Freio emergência\n'
               'A / D  →  Virar esq / dir            I / O   →  VelMax ±1\n'
               '                                      K / L   →  AngMax ±0.05')
        tk.Label(self.root, text=leg, bg=BG, fg=GREY,
                 font=('Monospace', 8), justify='left').pack(**pad)

        tk.Frame(self.root, bg=GREY, height=1).pack(fill='x', padx=14, pady=4)

        # barras
        self.canvas = tk.Canvas(self.root, width=440, height=70,
                                bg=BG2, highlightthickness=0)
        self.canvas.pack(padx=14, pady=4)

        # valores numéricos
        val_frame = tk.Frame(self.root, bg=BG)
        val_frame.pack(fill='x', padx=14)

        self.lbl_speed = tk.Label(val_frame, text='Speed:  +0.00 rad/s',
                                  bg=BG, fg=FG, font=('Monospace', 11), anchor='w')
        self.lbl_speed.grid(row=0, column=0, sticky='w', padx=(0, 30))

        self.lbl_vmax = tk.Label(val_frame, text='VelMax:  5.0 rad/s',
                                 bg=BG, fg=GREY, font=('Monospace', 11), anchor='e')
        self.lbl_vmax.grid(row=0, column=1, sticky='e')

        self.lbl_steer = tk.Label(val_frame, text='Steer:  +0.000 rad',
                                  bg=BG, fg=FG, font=('Monospace', 11), anchor='w')
        self.lbl_steer.grid(row=1, column=0, sticky='w')

        self.lbl_amax = tk.Label(val_frame, text='AngMax:  0.52 rad',
                                 bg=BG, fg=GREY, font=('Monospace', 11), anchor='e')
        self.lbl_amax.grid(row=1, column=1, sticky='e')

        val_frame.columnconfigure(0, weight=1)
        val_frame.columnconfigure(1, weight=1)

        tk.Frame(self.root, bg=GREY, height=1).pack(fill='x', padx=14, pady=4)

        # teclas ativas
        self.lbl_keys = tk.Label(self.root, text='Teclas: —',
                                 bg=BG, fg=GREY, font=('Monospace', 10))
        self.lbl_keys.pack()

        # e-stop
        self.lbl_estop = tk.Label(self.root, text='',
                                  bg=BG, fg=RED, font=('Monospace', 11, 'bold'))
        self.lbl_estop.pack(pady=(2, 10))

        # bindings
        self.root.bind('<KeyPress>',   self._on_press)
        self.root.bind('<KeyRelease>', self._on_release)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.focus_set()

    # ── eventos de teclado ────────────────────────────────────────────────────

    def _on_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        # Cancela remoção pendente (X11 key-repeat manda KeyRelease+KeyPress falsos)
        if key in self._rel_timers:
            self.root.after_cancel(self._rel_timers.pop(key))
        self._held.add(key)
        # Ajustes de limite (disparado uma vez por pressionada, com cooldown)
        if key in ('i', 'o', 'k', 'l'):
            now = time.monotonic()
            if now - self._adj_last.get(key, 0.0) >= ADJUST_COOLDOWN:
                self._adj_last[key] = now
                if   key == 'i': self._max_speed = min(MAX_SPEED,    self._max_speed + STEP_SPEED)
                elif key == 'o': self._max_speed = max(MIN_SPEED,    self._max_speed - STEP_SPEED)
                elif key == 'k': self._max_steer = min(MAX_STEER_CAP,self._max_steer + STEP_STEER)
                elif key == 'l': self._max_steer = max(MIN_STEER,    self._max_steer - STEP_STEER)
        if key == 'escape':
            self._on_close()

    def _on_release(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in self._rel_timers:
            self.root.after_cancel(self._rel_timers[key])
        # Delay de 80 ms: margem 2× sobre o intervalo de repeat do X11 (~33 ms).
        # Garante que o KeyPress de repeat chegue e cancele este timer antes
        # de remover a tecla do set, evitando que a direção "pisque".
        self._rel_timers[key] = self.root.after(80, self._remove, key)

    def _remove(self, key: str) -> None:
        self._rel_timers.pop(key, None)
        self._held.discard(key)

    # ── loop de física / publicação ───────────────────────────────────────────

    def _update(self) -> None:
        held = self._held.copy()

        w     = 'w'     in held
        s     = 's'     in held
        a     = 'a'     in held
        d     = 'd'     in held
        space = 'space' in held

        if space:
            self._speed  = 0.0
            self._steer *= 0.8
        else:
            # velocidade
            if w and not s:
                self._speed = min( self._max_speed, self._speed + SPEED_ACCEL * DT)
            elif s and not w:
                self._speed = max(-self._max_speed, self._speed - SPEED_BRAKE * DT)
            else:
                delta = SPEED_COAST * DT
                if abs(self._speed) <= delta:
                    self._speed = 0.0
                elif self._speed > 0:
                    self._speed -= delta
                else:
                    self._speed += delta

            # direção
            if a and not d:
                self._steer = min( self._max_steer, self._steer + STEER_RATE * DT)
            elif d and not a:
                self._steer = max(-self._max_steer, self._steer - STEER_RATE * DT)
            else:
                delta = STEER_RETURN * DT
                if abs(self._steer) <= delta:
                    self._steer = 0.0
                elif self._steer > 0:
                    self._steer -= delta
                else:
                    self._steer += delta

        # Publicar no ROS a cada PUB_EVERY ticks; sempre publicar freio de emergência
        self._pub_tick += 1
        if space or self._pub_tick >= PUB_EVERY:
            self.node.send(self._speed, self._steer)
            self._pub_tick = 0

        self._draw(space, held)
        self.root.after(LOOP_MS, self._update)

    # ── renderização ──────────────────────────────────────────────────────────

    def _draw(self, emergency: bool, held: set[str]) -> None:
        spd_col = RED if self._speed < -0.05 else (GREEN if self._speed > 0.05 else FG)
        str_col = CYAN if abs(self._steer) > 0.02 else FG

        self.lbl_speed.config(text=f'Speed:  {self._speed:+6.2f} rad/s', fg=spd_col)
        self.lbl_steer.config(text=f'Steer:  {self._steer:+6.3f} rad',   fg=str_col)
        self.lbl_vmax.config( text=f'VelMax: {self._max_speed:.1f} rad/s')
        self.lbl_amax.config( text=f'AngMax: {self._max_steer:.2f} rad')

        display_keys = sorted(k for k in held if k in ('w','s','a','d','space'))
        self.lbl_keys.config(
            text=f"Teclas: {' + '.join(display_keys) if display_keys else '—'}")
        self.lbl_estop.config(
            text='*** FREIO DE EMERGÊNCIA ***' if emergency else '')

        # barras no canvas
        c = self.canvas
        c.delete('all')
        W, H, MID = 440, 70, 220

        # fundo das barras
        c.create_rectangle(10, 8,  W-10, 30, fill='#22223a', outline='')
        c.create_rectangle(10, 40, W-10, 62, fill='#22223a', outline='')

        # barra de velocidade
        spd_px = int(abs(self._speed) / MAX_SPEED * (MID - 10))
        if self._speed >= 0:
            c.create_rectangle(MID, 8, MID + spd_px, 30, fill=GREEN, outline='')
        else:
            c.create_rectangle(MID - spd_px, 8, MID, 30, fill=RED, outline='')

        # barra de direção
        str_px = int(abs(self._steer) / MAX_STEER_CAP * (MID - 10))
        if self._steer >= 0:
            c.create_rectangle(MID, 40, MID + str_px, 62, fill=CYAN, outline='')
        else:
            c.create_rectangle(MID - str_px, 40, MID, 62, fill=CYAN, outline='')

        # linha central
        c.create_line(MID, 8, MID, 62, fill=GREY, width=1)

        # labels
        c.create_text(12,  19, text='SPEED', anchor='w', fill=GREY, font=('Monospace', 7))
        c.create_text(12,  51, text='STEER', anchor='w', fill=GREY, font=('Monospace', 7))

    # ── entrada / saída ───────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.node.send(0.0, 0.0)
        self.root.destroy()
        rclpy.shutdown()
        sys.exit(0)

    def run(self) -> None:
        self.root.after(LOOP_MS, self._update)
        self.root.mainloop()


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    rclpy.init()
    node = TeleopNode()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    TeleopGUI(node).run()
