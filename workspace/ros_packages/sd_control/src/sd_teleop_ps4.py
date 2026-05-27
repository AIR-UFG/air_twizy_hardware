#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from ackermann_msgs.msg import AckermannDriveStamped

# PS4 DualShock 4 — mapeamento validado em /dev/input/js0
AXIS_STEER    = 0   # Left stick X  | -1.0 (esq) → +1.0 (dir)
AXIS_BRAKE    = 4   # L2 trigger    | +1.0 (solto) → -1.0 (fundo)
AXIS_THROTTLE = 5   # R2 trigger    | +1.0 (solto) → -1.0 (fundo)
BTN_DEADMAN   = 9   # Options — segurar para habilitar controle
BTN_ESTOP     = 8   # Share   — parada de emergência
BTN_DPAD_UP   = 11  # D-pad ↑ — aumentar velocidade máxima
BTN_DPAD_DOWN = 12  # D-pad ↓ — diminuir velocidade máxima

# Limites físicos do vehicle_control_plugin
MAX_SPEED_RAD_S  = 5.0   # rad/s (~4.7 km/h) — limite inicial conservador
MAX_SPEED_STEP   = 1.0   # rad/s por toque no d-pad
MAX_SPEED_MIN    = 1.0
MAX_SPEED_MAX    = 10.0  # limite do plugin
MAX_STEER_RAD    = 0.52  # radianos (~30°)

HELP = """
╔══════════════════════════════════════════╗
║     Teleop PS4 — Renault Twizy Sim      ║
╠══════════════════════════════════════════╣
║  SEGURAR Options → habilitar controle   ║
║  R2 (gatilho)    → acelerar            ║
║  L2 (gatilho)    → frear              ║
║  Analógico esq   → direção             ║
║  Share           → parada emergência   ║
║  D-pad cima/baixo → vel. máxima        ║
╚══════════════════════════════════════════╝
Unidades: speed em rad/s | steer em rad
"""


def trigger_to_fraction(axis_val: float, initialized: bool) -> float:
    """Converte eixo de gatilho PS4 para 0.0–1.0."""
    if not initialized:
        return 0.0
    return max(0.0, (1.0 - axis_val) / 2.0)


class PS4Teleop(Node):
    def __init__(self):
        super().__init__('sd_teleop_ps4')

        self.pub = self.create_publisher(
            AckermannDriveStamped, '/sd_control/cmd_vel', 10)
        self.sub = self.create_subscription(
            Joy, 'joy', self._joy_cb, 10)

        self._max_speed  = MAX_SPEED_RAD_S
        self._r2_init    = False
        self._l2_init    = False
        self._dpad_prev  = 0.0
        self._prev_buttons = []

        self.get_logger().info(HELP)
        self.get_logger().info(
            f'Velocidade máxima inicial: {self._max_speed:.1f} rad/s')

    def _joy_cb(self, msg: Joy):
        cur_buttons = list(msg.buttons)

        # Detectar primeira vez que os gatilhos são tocados
        if msg.axes[AXIS_THROTTLE] != 0.0:
            self._r2_init = True
        if msg.axes[AXIS_BRAKE] != 0.0:
            self._l2_init = True

        # Parada de emergência — independe do deadman
        if msg.buttons[BTN_ESTOP]:
            self._publish(speed=0.0, steer=0.0)
            self.get_logger().warn('PARADA DE EMERGÊNCIA (Share)')
            self._prev_buttons = cur_buttons
            return

        # D-pad ajusta velocidade máxima (borda de subida nos botões)
        if self._prev_buttons:
            if self._prev_buttons[BTN_DPAD_UP] == 0 and cur_buttons[BTN_DPAD_UP] == 1:
                self._max_speed = min(MAX_SPEED_MAX, self._max_speed + MAX_SPEED_STEP)
                self.get_logger().info(f'Velocidade máxima: {self._max_speed:.1f} rad/s')
            if self._prev_buttons[BTN_DPAD_DOWN] == 0 and cur_buttons[BTN_DPAD_DOWN] == 1:
                self._max_speed = max(MAX_SPEED_MIN, self._max_speed - MAX_SPEED_STEP)
                self.get_logger().info(f'Velocidade máxima: {self._max_speed:.1f} rad/s')

        self._prev_buttons = cur_buttons

        throttle = trigger_to_fraction(msg.axes[AXIS_THROTTLE], self._r2_init)
        brake    = trigger_to_fraction(msg.axes[AXIS_BRAKE],    self._l2_init)
        steer    = msg.axes[AXIS_STEER] * MAX_STEER_RAD

        # Frear subtrai da velocidade; resultado pode ser negativo (ré)
        speed = (throttle - brake) * self._max_speed

        self.get_logger().info(
            f'speed={speed:.2f} rad/s  steer={steer:.3f} rad  '
            f'[thr={throttle:.2f} brk={brake:.2f}]',
            throttle_duration_sec=0.5
        )

        self._publish(speed=speed, steer=steer)

    def _publish(self, speed: float, steer: float):
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.speed          = speed
        msg.drive.steering_angle = steer
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = PS4Teleop()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        try:
            node._publish(speed=0.0, steer=0.0)
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
