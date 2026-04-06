import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node, SetRemap
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition

def generate_launch_description():

    # 1. GET PATHS
    # CHECK THIS: Make sure 'hw_bot' is your actual package name
    my_pkg_name = 'hw_bot' 
    pkg_share = get_package_share_directory(my_pkg_name)
    param_config = os.path.join(get_package_share_directory('hw_bot'), 'config', 'param.yaml')
 
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_nav2_bt_navigator = get_package_share_directory('nav2_bt_navigator')

    # Path to your param file
    # Note: Using the file from your previous prompts
    default_params_file = os.path.join(pkg_share, 'config', 'nav2_params_rgbd.yaml')

    # 2. ARGUMENTS
    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the ROS2 parameters file to use for all launched nodes')

    declare_bt_xml_cmd = DeclareLaunchArgument(
        'default_bt_xml_filename',
        default_value=os.path.join(
            pkg_nav2_bt_navigator,
            'behavior_trees', 'navigate_w_replanning_and_recovery.xml'),
        description='Full path to the behavior tree xml file to use')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart', default_value='true',
        description='Automatically startup the nav2 stack')
    
    localization_arg = DeclareLaunchArgument(
        'localization', default_value='false',
        description='true for localization mode (AMCL/RTAB-Loc), false for mapping mode'
    )

    # Default to false for real robot hardware
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

    # 3. NODES AND LAUNCHES

    # A. RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_share, 'rviz', LaunchConfiguration('rviz_config')])],
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    # B. Depth Image to LaserScan (The Bridge)
    # This converts RealSense 3D data to 2D scan for Nav2
    depthimage_to_laserscan = Node(
            package='depthimage_to_laserscan',
            executable='depthimage_to_laserscan_node',
            name='depthimage_to_laserscan_node',
            remappings=[
                # Subscribe to the Rectified Raw Depth image
                ('depth', '/camera/aligned_depth_to_color/image_raw'),
                # Subscribe to the Camera Info
                ('depth_camera_info', '/camera/aligned_depth_to_color/camera_info'),
                # Publish the 2D scan (mapped to rgbd_scan to match your param.yaml)
                ('scan', '/rgbd_scan') 
            ],
            parameters=[param_config] # Ensure this frame matches your URDF camera link name
        )

    # C. RTAB-Map (SLAM or Localization)
    # Assumes you have a launch file named rtabmap_sim.launch.py in your package
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'realsense_d435i_color.launch.py') 
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'localization': LaunchConfiguration('localization')
        }.items()
    )

    # D. Nav2 (Navigation Stack)
    nav2_launch_group = GroupAction(
        actions=[
            SetRemap(src='/cmd_vel_smoothed', dst='/cmd_vel'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
                ),
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'params_file': LaunchConfiguration('params_file'), # Pass the arg, don't hardcode
                    'autostart': LaunchConfiguration('autostart'),
                    'use_composition': 'False',
                }.items()
            )
        ]
    )
    
    
    return LaunchDescription([
        declare_params_file_cmd,
        declare_bt_xml_cmd,
        declare_autostart_cmd,
        rviz_launch_arg,
        rviz_config_arg,
        localization_arg,
        use_sim_time_arg,
        
        # Launch everything
        depthimage_to_laserscan, # Start the sensor bridge first
        rviz_node,
        rtabmap_launch,
        nav2_launch_group,
    ])