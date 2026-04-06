from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument

import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. Declare Launch Arguments
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 2. Get YAML parameter file path
    joy_params = os.path.join(
        get_package_share_directory('hw_bot'),
        'config',
        'joystick.yaml'
    )

    # 3. joy_node: Reads raw joystick data
    joy_node = Node(
            package='joy',
            executable='joy_node',
            parameters=[joy_params, {'use_sim_time': use_sim_time}],
         )

    # 4. teleop_node: Converts raw data to Twist messages
    teleop_node = Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_node',
            parameters=[joy_params, {'use_sim_time': use_sim_time}],
            
            # 💡 CRITICAL CHANGE: Remap default '/cmd_vel' output to the controller's input topic
            remappings=[
                ('/cmd_vel','diff_cont/cmd_vel_unstamped')
            ]
         )

    # Note: The twist_stamper node is still commented out as it is not needed if the
    # controller accepts an unstamped Twist message directly.

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use sim time if true'),
        joy_node,
        teleop_node,
        # twist_stamper
    ])