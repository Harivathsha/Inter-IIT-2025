import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetRemap
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition

def generate_launch_description():

    # 1. GET PATHS
    pkg_hv_bot_arm = get_package_share_directory('hw_bot')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # 2. ARGUMENTS
    localization_arg = DeclareLaunchArgument(
        'localization', default_value='true',
        description='true for localization mode, false for mapping mode'
    )

    # CHANGE: Default to false for real robot
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation clock'
    )

    rviz_launch_arg = DeclareLaunchArgument(
        'rviz', default_value='true',
        description='Open RViz'
    )

    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config', default_value='navigation.rviz',
        description='RViz config file'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_hv_bot_arm, 'rviz', LaunchConfiguration('rviz_config')])],
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    # 3. DEFINE NODES/LAUNCHES
    
    # A. Your Simulation (Commented out for Real Robot)
    # launch_sim = IncludeLaunchDescription(...)

    # B. RTAB-Map
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_hv_bot_arm, 'launch', 'realsense_d435i_color.launch.py') 
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'), # CHANGE: Pass the arg, don't hardcode 'true'
            'localization': LaunchConfiguration('localization')
        }.items()
    )

    # C. Nav2
    nav2_launch_group = GroupAction(
        actions=[
            SetRemap(src='/cmd_vel_smoothed', dst='/cmd_vel'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
                ),
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'), # CHANGE: Pass the arg, don't hardcode 'true'
                    'params_file': os.path.join(pkg_hv_bot_arm, 'config', 'nav2_params.yaml'),
                    'autostart': 'True',
                    'use_composition': 'False',
                }.items()
            )
        ]
    )
    
    return LaunchDescription([
        rviz_launch_arg,
        rviz_config_arg,
        localization_arg,
        use_sim_time_arg,
        rviz_node,
        rtabmap_launch,
        nav2_launch_group,
    ])