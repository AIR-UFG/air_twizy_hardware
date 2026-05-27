#!/usr/bin/env python3
"""
Teleop PS4 para o carro real.
Publica DirectControl em direct_control_cmd — formato esperado pelo sd_vehicle_interface.

Mapeamento PS4 validado (/dev/input/js0):
  axes[0] = LX          : direção (-1 esq → +1 dir)
  axes[4] = L2          : frear   (+1 solto → -1 fundo)
  axes[5] = R2          : acelerar (+1 solto → -1 fundo)
  buttons[8] = Share    : parada de emergência
  buttons[9] = Options  : deadman (segurar para habilitar)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from sd_msgs.msg import DirectControl

AXIS_STEER    = 0
AXIS_BRAKE    = 4
AXIS_THROTTLE = 5
BTN_ESTOP     = 8
BTN_DEADMAN   = 9

MAX_TORQUE = 30    # % — valor conservador inicial
MAX_STEER  = 100   # % — limite de direção
MAX_BRAKE  = -40   # % — freio máximo


def trigger_to_fraction(val: float, initialized: bool) -> float:
    if not initialized:
        return 0.0
    return max(0.0, (1.0 - val) / 2.0)


class PS4DirectTeleop(Node):
    def __init__(self):
        super().__init__('sd_teleop_ps4_direct')
        self.pub = self.create_publisher(DirectControl, 'direct_control_cmd', 10)
        self.sub = self.create_subscription(Joy, 'joy', self._joy_cb, 10)

        self._r2_init = False
        self._l2_init = False
        self._prev_buttons = []

        self.get_logger().info(
            'PS4 Direct Teleop iniciado\n'
            '  Segurar Options → habilitar controle\n'
            '  R2 → acelerar | L2 → frear | Analógico esq → direção\n'
            '  Share → parada de emergência\n'
            f'  Torque máx: {MAX_TORQUE}%  Freio máx: {MAX_BRAKE}%  Steer máx: {MAX_STEER}%'
        )

    def _joy_cb(self, msg: Joy):
        if msg.axes[AXIS_THROTTLE] != 0.0:
            self._r2_init = True
        if msg.axes[AXIS_BRAKE] != 0.0:
            self._l2_init = True

        cur = list(msg.buttons)

        if len(cur) > BTN_ESTOP and cur[BTN_ESTOP]:
            self._publish(0.0, 0.0)
            self.get_logger().warn('PARADA DE EMERGÊNCIA (Share)')
            self._prev_buttons = cur
            return

        deadman = len(cur) > BTN_DEADMAN and cur[BTN_DEADMAN]
        if not deadman:
            self._publish(0.0, 0.0)
            self._prev_buttons = cur
            return

        throttle = trigger_to_fraction(msg.axes[AXIS_THROTTLE], self._r2_init)
        brake    = trigger_to_fraction(msg.axes[AXIS_BRAKE],    self._l2_init)
        steer    = msg.axes[AXIS_STEER] * MAX_STEER

        if brake > 0:
            torque = brake * MAX_BRAKE
        else:
            torque = throttle * MAX_TORQUE

        self.get_logger().info(
            f'torque={torque:.1f}%  steer={steer:.1f}%  '
            f'[thr={throttle:.2f} brk={brake:.2f}]',
            throttle_duration_sec=0.5
        )
        self._publish(torque, steer)
        self._prev_buttons = cur

    def _publish(self, torque: float, steer: float):
        msg = DirectControl()
        msg.torque_setpoint = float(torque)
        msg.steer_setpoint  = float(steer)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = PS4DirectTeleop()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        try:
            node._publish(0.0, 0.0)
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
