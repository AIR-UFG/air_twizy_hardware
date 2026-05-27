from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy',
            executable='joy_node',
            name='joy',
            parameters=[{'deadzone': 0.1, 'autorepeat_rate': 20.0}]
        ),
        Node(
            package='sd_control',
            executable='sd_teleop_ps4.py',
            name='sd_teleop_ps4',
            output='screen'
        ),
    ])
