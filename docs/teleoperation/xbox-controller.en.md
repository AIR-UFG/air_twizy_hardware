# Xbox Controller Interface

The teleoperation stack uses an Xbox controller (USB or Bluetooth) on the operator's machine to generate drive commands sent to the vehicle over the NetBird VPN.

## Button Mapping (Direct Control mode)

| Command | Button/Axis | Technical Description |
|---------|------------|----------------------|
| Accelerate | RT (Right Trigger) | Sets positive torque setpoint |
| Brake | LT (Left Trigger) | Sets negative torque setpoint |
| Steer | Left Analog Stick | Controls front wheel angle |
| Safety center | LB button | Immediately centers steering |
| Increase speed limit | Y button | Raises maximum velocity limit |
| Decrease speed limit | B button | Lowers maximum velocity limit |
| Increase brake intensity | X button | Increases braking force |
| Decrease brake intensity | A button | Decreases braking force |

!!! note "Speed-dependent steering"
    `direct_teleop` applies a lookup table that automatically limits the steering angle as vehicle speed increases — wider turns are blocked at high speed.

## Custom ROS2 Messages

### DirectControl.msg (operator → vehicle)

```
float64 linear_velocity    # linear velocity (optional)
float64 torque_setpoint    # -100 (full brake) to +100 (full throttle)
float64 steer_setpoint     # -100 (right) to +100 (left)
```

### SDControl.msg (vehicle → operator, feedback)

```
std_msgs/Header header
float64 steer              # current steering angle
float64 torque             # current torque
float64 current_velocity   # measured vehicle speed
float64 target_velocity    # target speed setpoint
int32   p, d, i, ff        # velocity PID terms
int32   steer_p, steer_i, steer_d  # steering PID terms
float64 steer_actual       # actual steering angle from sensor
```

## Joystick device access in Docker

The teleop container needs access to the host's input devices:

```yaml
volumes:
  - /dev/input:/dev/input:rw    # access to input drivers
  - /run/udev:/run/udev:ro      # correct joystick identification via udev
devices:
  - /dev/input                  # explicit permission for Xbox controller
```

## Verifying the joystick is detected

```bash
# On the host (before starting Docker)
ls /dev/input/js*
# Should show /dev/input/js0 (or similar)

# Inside the container
ros2 run joy joy_node --ros-args -r /joy:=joy_teleop_test
ros2 topic echo /joy_teleop_test
# Move a stick — values should change in the output
```
