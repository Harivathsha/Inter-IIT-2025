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
    my_pkg_name = 'hw_bot'
    pkg_share = get_package_share_directory(my_pkg_name)
    param_config = os.path.join(pkg_share, 'config', 'param.yaml')
 
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')
    pkg_nav2_bt_navigator = get_package_share_directory('nav2_bt_navigator')

    # Default params file
    default_params_file = os.path.join(pkg_share, 'config', 'nav2_params_rgbd.yaml')

    # 2. ARGUMENTS
    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to the ROS2 parameters file')

    declare_bt_xml_cmd = DeclareLaunchArgument(
        'default_bt_xml_filename',
        default_value=os.path.join(
            pkg_nav2_bt_navigator,
            'behavior_trees', 'navigate_w_replanning_and_recovery.xml'),
        description='Full path to the behavior tree xml file')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart', default_value='True',
        description='Automatically startup the nav2 stack')
    
    # NEW ARGUMENT: Path to the map file to load
    declare_map_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_share, 'maps', 'rs_map2.yaml'),
        description='Full path to map yaml file to load')

    # SLAM Flag: Default to False (Navigation Mode)
    declare_slam_cmd = DeclareLaunchArgument(
        'slam', default_value='False',
        description='Whether to run SLAM (True) or Localization/Nav (False)')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='False',
        description='Use simulation clock')

    rviz_launch_arg = DeclareLaunchArgument(
        'rviz', default_value='True',
        description='Open RViz')

    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config', default_value='navigation.rviz',
        description='RViz config file')

    # 3. LOGIC GENERATION
    # Create a variable that is the INVERSE of slam.
    # If slam='True', localization='False'. If slam='False', localization='True'.
    # We use strings 'True'/'False' to prevent the "name 'true' is not defined" error.
    localization_bool = PythonExpression([
        '"False" if "', LaunchConfiguration('slam'), '" == "True" else "True"'
    ])

    # 4. NODES AND LAUNCHES

    # A. RViz Node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_share, 'rviz', LaunchConfiguration('rviz_config')])],
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # B. Depth Image to LaserScan
    depthimage_to_laserscan = Node(
            package='depthimage_to_laserscan',
            executable='depthimage_to_laserscan_node',
            name='depthimage_to_laserscan_node',
            remappings=[
                ('depth', '/camera/aligned_depth_to_color/image_raw'),
                ('depth_camera_info', '/camera/aligned_depth_to_color/camera_info'),
                ('scan', '/rgbd_scan') 
            ],
            parameters=[param_config]
        )

    # C. RTAB-Map
    # Uses the 'localization_bool' we created above.
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'realsense_d435i_color.launch.py') 
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'localization': localization_bool
        }.items()
    )

    # D. Nav2 (Navigation Stack)
    nav2_launch_group = GroupAction(
        actions=[
            SetRemap(src='/cmd_vel_smoothed', dst='/cmd_vel'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav2_bringup, 'launch', 'bringup_launch.py')
                ),
                launch_arguments={
                    'use_sim_time': LaunchConfiguration('use_sim_time'),
                    'params_file': LaunchConfiguration('params_file'),
                    'autostart': LaunchConfiguration('autostart'),
                    'use_composition': 'False',
                    'map': LaunchConfiguration('map'),
                    'slam': LaunchConfiguration('slam'), 
                }.items()
            )
        ]
    )
    
    return LaunchDescription([
        declare_params_file_cmd,
        declare_bt_xml_cmd,
        declare_autostart_cmd,
        declare_map_cmd,
        declare_slam_cmd,
        rviz_launch_arg,
        rviz_config_arg,
        use_sim_time_arg,
        
        # Launch everything
        depthimage_to_laserscan,
        rviz_node,
        rtabmap_launch,
        nav2_launch_group,
    ])