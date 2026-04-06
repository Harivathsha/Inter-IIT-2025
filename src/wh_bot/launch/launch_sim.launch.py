import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # !!! MAKE SURE YOU SET THE PACKAGE NAME CORRECTLY !!!
    package_name='wh_bot' 

    pkg_hv_bot_arm = get_package_share_directory(package_name)
    gazebo_models_path, ignore_last_dir = os.path.split(pkg_hv_bot_arm)

    # Path to the controller YAML file
    robot_controllers = PathJoinSubstitution(
        [
            get_package_share_directory(package_name),
            'config',
            'my_controllers.yaml',
        ]
    )

    # Add gazebo model path
    if "GZ_SIM_RESOURCE_PATH" in os.environ:
        os.environ["GZ_SIM_RESOURCE_PATH"] += os.pathsep + gazebo_models_path
    else:
        os.environ["GZ_SIM_RESOURCE_PATH"] = gazebo_models_path

    # Launch Arguments
    rviz_launch_arg = DeclareLaunchArgument(
        'rviz', default_value='true',
        description='Open RViz'
    )
    sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='True',
        description='Flag to enable use_sim_time'
    )
    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config', default_value='main.rviz',
        description='RViz config file'
    )

    # Robot State Publisher
    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name),'launch','rsp.launch.py'
                )]), launch_arguments={'use_sim_time': 'true', 'use_ros2_control': 'true'}.items()
    )

    # World Config
    default_world = os.path.join(
        get_package_share_directory(package_name),
        'worlds',
        'empty_new.world'
        )    
    
    world = LaunchConfiguration('world')
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=default_world,
        description='World to load'
        )

    # Gazebo Sim
    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
                    launch_arguments={'gz_args': ['-r -v4 ', world], 'on_exit_shutdown': 'true'}.items()
             )

    # RViz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_hv_bot_arm, 'rviz', LaunchConfiguration('rviz_config')])],
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    # Spawn Robot
    spawn_entity = Node(
        package='ros_gz_sim', 
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'wh_bot',
            '-x', '-2.74',    
            '-y', '-3.86',    
            '-z', '0.0210',    
            '-Y', '0'    
        ],
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # ---------------------------------------------------------
    # CONTROLLER SPAWNERS
    # ---------------------------------------------------------

    # 1. Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    # 2. Torso Controller
    joint_trajectory_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'torso_controller',
            '--param-file',
            robot_controllers,
            ],
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )


    # 3. Diff Drive Controller
    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont'],
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    # ---------------------------------------------------------
    # TOPIC RELAYS (REMAPPING FIX)
    # ---------------------------------------------------------

    # Relay 1: ODOM (Controller -> Root)
    # Takes /diff_drive_base_controller/odom and publishes it to /odom
    odom_relay = Node(
        package='topic_tools',
        executable='relay',
        arguments=['/diff_cont/odom', '/odom'],
        output='screen',
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition("true") 
    )


    bridge_params = os.path.join(get_package_share_directory(package_name),'config','gz_bridge.yaml')
    ros_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ],
        output="screen",
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')},
        ]
    )

    
    return LaunchDescription([
        rviz_launch_arg,
        rviz_config_arg,
        sim_time_arg,
        rsp,
        # twist_mux,
        world_arg,
        gazebo,
        spawn_entity,
        rviz_node,
        joint_state_broadcaster_spawner,
        joint_trajectory_controller_spawner,
        diff_drive_spawner,
        odom_relay,
        ros_gz_bridge
    ])