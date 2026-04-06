import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # 1. GET PATHS
    pkg_hv_bot_arm = get_package_share_directory('wh_bot')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # 2. ARGUMENTS
    localization_arg = DeclareLaunchArgument(
        'localization', default_value='false',
        description='true for localization mode, false for mapping mode'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation clock'
    )

    # 3. DEFINE NODES/LAUNCHES
    
    # A. Your Simulation (We let THIS launch RViz)
    # launch_sim = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(pkg_hv_bot_arm, 'launch', 'launch_sim.launch.py')
    #     ),
    #     launch_arguments={
    #         'use_sim_time': 'true',
    #         'rviz': 'true',                     # Turn RViz ON inside the sim launch
    #         'rviz_config': 'navigation.rviz'    # Tell it to use your navigation config
    #     }.items() 
    # )

    # B. RTAB-Map
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_hv_bot_arm, 'launch', 'rtabmap_sim.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'localization': LaunchConfiguration('localization')
        }.items()
    )

    # C. Nav2
    # C. Nav2
    # C. Nav2 (WRAPPED IN GROUP ACTION FOR REMAPPING)
    # This forces the "smoothened" topic back to normal "/cmd_vel"
    nav2_launch_group = GroupAction(
        actions=[
            SetRemap(src='/cmd_vel_smoothed', dst='/cmd_vel'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
                ),
                launch_arguments={
                    'use_sim_time': 'true',
                    'params_file': os.path.join(pkg_hv_bot_arm, 'config', 'navigation_3d.yaml'),
                    'autostart': 'True',
                    'use_composition': 'False',
                }.items()
            )
        ]
    )
    return LaunchDescription([
        localization_arg,
        use_sim_time_arg,
        
        # launch_sim,
        rtabmap_launch,
        nav2_launch_group,
    ])