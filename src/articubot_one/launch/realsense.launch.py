import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    ld = LaunchDescription()

    # --- Configuration Variables ---
    enable_gyro = LaunchConfiguration('enable_gyro')
    enable_accel = LaunchConfiguration('enable_accel')
    unite_imu_method = LaunchConfiguration('unite_imu_method')
    enable_sync = LaunchConfiguration('enable_sync')
    
    # --- Declare Arguments ---
    declare_enable_gyro = DeclareLaunchArgument(
        'enable_gyro', default_value='true',
        description='Enable Gyroscope')
    
    declare_enable_accel = DeclareLaunchArgument(
        'enable_accel', default_value='true',
        description='Enable Accelerometer')
    
    declare_unite_imu_method = DeclareLaunchArgument(
        'unite_imu_method', default_value='2', 
        description='1: Copy, 2: Linear Interpolation. 2 is recommended for RTAB-Map.')
    
    declare_enable_sync = DeclareLaunchArgument(
        'enable_sync', default_value='true',
        description='Enable Emitter On/Off Sync')

    # --- Paths ---
    # Path to the standard RealSense launch file
    realsense_share_dir = get_package_share_directory('realsense2_camera')
    
    # Path to your custom Articubot launch file
    articubot_share_dir = get_package_share_directory('articubot_one')
    
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("articubot_one"), "rviz", "rtabmap.rviz"])

    # --- Nodes/Includes ---

    # 1. Launch RealSense Camera
    # CRITICAL FIX: Added 'align_depth.enable': 'true'
    start_rs = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(realsense_share_dir, 'launch', 'rs_launch.py')),
        launch_arguments={
            'enable_gyro': enable_gyro,
            'enable_accel': enable_accel,
            'unite_imu_method': unite_imu_method,
            'enable_sync': enable_sync,
            'align_depth.enable': 'true',  # Essential for RGB-D SLAM
        }.items()
    )

    # 2. Launch RTAB-Map (Your custom file)
    start_rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(articubot_share_dir, 'launch', 'realsense_d435i_color.launch.py'))
    )

    # 3. Launch RViz
    visu_rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file]
    )

    # --- Add Actions ---
    ld.add_action(declare_enable_gyro)
    ld.add_action(declare_enable_accel)
    ld.add_action(declare_unite_imu_method)
    ld.add_action(declare_enable_sync)
    ld.add_action(start_rs)
    ld.add_action(start_rtabmap)
    ld.add_action(visu_rviz)

    return ld