import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node

def generate_launch_description():

    use_sim_time = LaunchConfiguration('use_sim_time')
    qos = LaunchConfiguration('qos')
    localization = LaunchConfiguration('localization')

    # --- CONFIGURATION BASED ON YOUR WORKING SNIPPET ---
    parameters = {
        'frame_id': 'base_link',     # Ensure this matches your URDF (might be base_link)
        'use_sim_time': use_sim_time,

        # Input configuration (Crucial: Using PointCloud, not Depth Image)
        'subscribe_depth': False,           
        'subscribe_scan_cloud': True,       
        'subscribe_rgb': True,              
        'subscribe_scan': False,            # Assuming we rely on camera, not 2D LiDAR
        
        # Tuning for Simulation
        'approx_sync': True,                # CRITICAL for Gazebo synchronization
        'queue_size': 20,                   # Helps if topics are laggy

        # RTAB-Map Internal Logic
        'use_action_for_goal': True,
        'qos_image': qos,
        'qos_imu': qos,
        'Reg/Force3DoF': 'true',            # Force 2D constraints (robot can't fly)
        'Optimizer/GravitySigma': '0',      # Ignore IMU gravity
        'RGBD/NeighborLinkRefining': 'true', # Aligns scans better
        
        # If true, it saves the map to ~/.ros/rtabmap.db
        # If false (Localization mode), it stops updating the map
        'Mem/IncrementalMemory': 'true', 
    }
    
    # Overwrite parameter for Localization Mode
    # If localization=true, we turn OFF map updating
    localization_params = {
        'Mem/IncrementalMemory': 'false',
        'Mem/InitWMWithAllNodes': 'true'
    }

    remappings = [
        # --- YOUR SPECIFIC TOPICS ---
        ('rgb/image', '/rgb_camera'),
        ('rgb/camera_info', '/rgb_camera/camera_info'),
        ('scan_cloud', '/kinect_camera/points'),
        ('odom', '/odom'),
        
        # Output Map for Nav2
        ('grid_map', '/map')
    ]

    return LaunchDescription([

        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation (Gazebo) clock if true'),

        DeclareLaunchArgument(
            'qos', default_value='2',
            description='QoS used for input sensor topics'),

        DeclareLaunchArgument(
            'localization', default_value='false',
            description='Launch in localization mode.'),

        # SLAM Mode (Mapping)
        Node(
            condition=UnlessCondition(localization),
            package='rtabmap_slam', 
            executable='rtabmap', 
            output='screen',
            parameters=[parameters],
            remappings=remappings,
            arguments=['-d'] # Delete previous map on start (optional, remove -d to keep map)
        ),

        # Localization Mode
        Node(
            condition=IfCondition(localization),
            package='rtabmap_slam', 
            executable='rtabmap', 
            output='screen',
            parameters=[parameters, localization_params],
            remappings=remappings
        ),

        # RTAB-Map Visualizer (Optional, distinct from RViz)
        Node(
            package='rtabmap_viz', 
            executable='rtabmap_viz', 
            output='screen',
            parameters=[parameters],
            remappings=remappings
        ),
    ])