#!/usr/bin/env python3

import rclpy
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterType
import tf_transformations 
import time
import serial

class NavGoalSender(Node):
    """
    Sends navigation goals, communicates with ESP32, and dynamically limits speed.
    """
    def __init__(self, goals):
        super().__init__('nav_goal_sender')
        
        # --- CONFIGURATION ---
        self.goals = goals  
        self.goal_index = 0
        
        # Serial Port Configuration
        self.serial_port = '/dev/ttyUSB1'
        self.baud_rate = 115200 
        self.ser = None
        
        # Logic State
        self.next_action_is_up = True 
        self.expected_response = ""
        
        self.get_logger().info('Navigation Goal Sender Node has started.')

        # --- STEP 1: SET SPEED LIMIT DYNAMICALLY ---
        # We attempt to set the max speed to 0.05 m/s before doing anything else
        self.set_nav2_speed(0.05)
        
        # Initialize Serial Connection
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            self.ser.reset_input_buffer()
            self.get_logger().info(f"Connected to ESP32 on {self.serial_port}")
        except Exception as e:
            self.get_logger().error(f"Failed to connect to Serial Port: {e}")
        
        self._action_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        
        self.get_logger().info("Waiting for '/navigate_to_pose' action server...")
        self._action_client.wait_for_server()
        
        # Start the first goal
        self.send_next_goal()

    def set_nav2_speed(self, max_speed):
        """
        Dynamically sets the max_vel_x parameter of the Nav2 Controller.
        NOTE: This assumes the standard 'FollowPath' plugin name for DWB.
        """
        self.get_logger().info(f"Attempting to set max speed to {max_speed} m/s...")
        
        # Create a client to talk to the controller server parameter service
        param_client = self.create_client(SetParameters, '/controller_server/set_parameters')
        
        if not param_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn("Controller Server not available. Could not set speed!")
            return

        request = SetParameters.Request()
        
        # Define the parameter to change. 
        # Standard DWB Local Planner uses 'FollowPath.max_vel_x'
        # If you use MPPI or RPP, this name might be different (e.g., 'max_vel_x' or 'limit_vel')
        param = Parameter()
        param.name = 'FollowPath.max_vel_x'
        param.value.type = ParameterType.PARAMETER_DOUBLE
        param.value.double_value = max_speed
        
        request.parameters = [param]
        
        future = param_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        result = future.result()
        if result is not None and result.results[0].successful:
            self.get_logger().info(f"Successfully set speed to {max_speed} m/s")
        else:
            self.get_logger().warn("Failed to set speed parameter. Check your controller plugin name.")

    def send_next_goal(self):
        """Unpacks the current goal from the list and sends it."""
        if self.goal_index >= len(self.goals):
            self.get_logger().info("All goals completed successfully!")
            self.shutdown_node()
            return

        x, y, yaw, perform_action = self.goals[self.goal_index]
        self.get_logger().info(f"--- Processing Goal {self.goal_index + 1}/{len(self.goals)} ---")
        self.send_goal(x, y, yaw)

    def send_goal(self, x, y, yaw):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = 0.0

        q = tf_transformations.quaternion_from_euler(0, 0, yaw * 3.14159 / 180.0)
        goal_msg.pose.pose.orientation.x = q[0]
        goal_msg.pose.pose.orientation.y = q[1]
        goal_msg.pose.pose.orientation.z = q[2]
        goal_msg.pose.pose.orientation.w = q[3]

        self.get_logger().info(f"Sending goal: (x={x}, y={y}, yaw={yaw} deg)")

        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback)

        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal was REJECTED by the server!')
            self.shutdown_node()
            return

        self.get_logger().info('Goal ACCEPTED! Moving...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        pass
        # feedback = feedback_msg.feedback
        # self.get_logger().info(f'Dist remaining: {feedback.distance_remaining:.2f} m')

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Goal {self.goal_index + 1} SUCCEEDED.')
            
            current_goal_requires_action = self.goals[self.goal_index][3]

            if current_goal_requires_action:
                self.trigger_esp32_sequence()
            else:
                self.get_logger().info("No action required here. Waiting 2 seconds...")
                self.goal_index += 1
                self.wait_timer = self.create_timer(2.0, self.wait_timer_callback)

        else:
            self.get_logger().error(f'Goal failed with status: {status}. Stopping.')
            self.shutdown_node()

    def trigger_esp32_sequence(self):
        if self.ser is None:
            self.get_logger().error("Serial port not available. Skipping action.")
            self.goal_index += 1
            self.send_next_goal()
            return

        command = ""
        if self.next_action_is_up:
            command = "up"
            self.expected_response = "max_u"
        else:
            command = "down"
            self.expected_response = "max_d"
            
        self.get_logger().info(f"Sending '{command}' to ESP32. Waiting for '{self.expected_response}'...")

        try:
            self.ser.write(command.encode('utf-8'))
        except Exception as e:
            self.get_logger().error(f"Error writing to serial: {e}")

        self.serial_timer = self.create_timer(0.1, self.check_serial_response)

    def check_serial_response(self):
        if self.ser and self.ser.in_waiting > 0:
            try:
                raw = self.ser.readline()
                if not raw:
                    return
                try:
                    line = raw.decode('utf-8').strip()
                except UnicodeDecodeError:
                    return

                if line:
                    self.get_logger().info(f"ESP32 says: {line}")

                if line == self.expected_response:
                    self.get_logger().info(f"Received confirmation: {line}")
                    self.serial_timer.cancel()
                    self.next_action_is_up = not self.next_action_is_up
                    self.goal_index += 1
                    self.send_next_goal()

            except Exception as e:
                self.get_logger().warn(f"Serial read error: {e}")

    def wait_timer_callback(self):
        self.wait_timer.cancel()
        self.send_next_goal()

    def shutdown_node(self):
        self.get_logger().info('Shutting down node.')
        if self.ser:
            self.ser.close()
        time.sleep(1)
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)

    # --- DEFINE YOUR LIST OF GOALS HERE ---
    goal_list = [
        (0.2, 0.0, 0.0, False),
        (0.4, 0.0, 0.0, True), 
        (0.6, 0.0, 0.0, False),
        (0.8, 0.0, 0.0, True),
    ]
    # --------------------------------------

    action_client_node = NavGoalSender(goal_list)

    try:
        rclpy.spin(action_client_node)
    except KeyboardInterrupt:
        action_client_node.get_logger().info('Keyboard interrupt.')
    except Exception:
        pass
    finally:
        if rclpy.ok():
            action_client_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()