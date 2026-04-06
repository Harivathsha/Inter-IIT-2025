import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node, SetParameter
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    
    # --- 1. PARAMETERS ---
    parameters=[{
          'frame_id':'base_link',
          'subscribe_depth':True,
          'subscribe_odom_info':False,
          'subscribe_odom':True,          # We listen to your robot's wheel odom
          'odom_frame_id': 'odom',
          'approx_sync':True,             # Required to sync wheels with camera
          'wait_imu_to_init':False,
          
          # --- DRIFT FIXES (Prevents Map Stitching) ---
          'Reg/Force3DoF': 'true',        # Keeps map flat (2D mode) so it doesn't tilt
          'RGBD/ProximityBySpace': 'true',# Search for loop closures by distance, not just image match
          'RGBD/AngularUpdate': '0.05',   # Update map more often (every ~3 degrees)
          'RGBD/LinearUpdate': '0.05',    # Update map every 5cm
          'RGBD/NeighborLinkRefining':'true', # Fixes small alignment errors between nodes
          'Reg/Strategy': '0',

        #   # Depth/registration
          'RGBD/MaxDepth': 4.0,
          'RGBD/MinDepth': 0.2,
          'Optimizer':3.0,                                # 0=Visual, 1=ICP (Use 1 if you have white walls/no texture)
    }]

    remappings=[
          ('imu', '/imu/data'),
          ('rgb/image', '/camera/color/image_raw'),
          ('rgb/camera_info', '/camera/color/camera_info'),
          ('depth/image', '/camera/aligned_depth_to_color/image_raw'),
          ('odom', '/diff_cont/odom')]    # <--- Your specific wheel odom topic

    return LaunchDescription([

        # Launch arguments
        DeclareLaunchArgument(
            'unite_imu_method', default_value='2',
            description='0-None, 1-copy, 2-linear_interpolation.'),

        # Make sure IR emitter is enabled
        SetParameter(name='depth_module.emitter_enabled', value=1),
        
        DeclareLaunchArgument(
            'args', default_value='',
            description='Extra arguments set to rtabmap nodes.'),
        
        # --- 2. LAUNCH CAMERA ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('realsense2_camera'), 'launch'),
                '/rs_launch.py']),
                launch_arguments={'camera_namespace': '',
                                  'enable_gyro': 'true',
                                  'enable_accel': 'true',
                                  'unite_imu_method': LaunchConfiguration('unite_imu_method'),
                                  'align_depth.enable': 'true',
                                  'enable_sync': 'true',
                                  'rgb_camera.profile': '640x360x30'}.items(),
        ),

        # --- 3. RTAB-MAP SLAM (Main Node) ---
        # NOTE: 'rgbd_odometry' node is DELETED. We use this SLAM node + your wheel odom.
        Node(
            package='rtabmap_slam', executable='rtabmap', output='screen',
            parameters=parameters,
            remappings=remappings,
            arguments=['-d', LaunchConfiguration("args")]),

        # --- 4. VISUALIZATION ---
        Node(
            package='rtabmap_viz', executable='rtabmap_viz', output='screen',
            parameters=parameters,
            remappings=remappings),

        # --- 5. IMU FILTER (Optional) ---
        Node(
            package='imu_filter_madgwick', executable='imu_filter_madgwick_node', output='screen',
            parameters=[{'use_mag': False, 
                         'world_frame':'enu', 
                         'publish_tf':False}],
            remappings=[('imu/data_raw', '/camera/imu')]),
    ])