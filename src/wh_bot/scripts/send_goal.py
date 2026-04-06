#!/usr/bin/env python3

import rclpy
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
import tf_transformations 
import time

class NavGoalSender(Node):
    """
    Sends a sequence of navigation goals to Nav2.
    """
    def __init__(self, goals):
        super().__init__('nav_goal_sender')
        self.goals = goals  # List of (x, y, yaw)
        self.goal_index = 0
        
        self.get_logger().info('Navigation Goal Sender Node has started.')
        self._action_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        
        # Wait for server once at startup
        self.get_logger().info("Waiting for '/navigate_to_pose' action server...")
        self._action_client.wait_for_server()
        
        # Start the first goal
        self.send_next_goal()

    def send_next_goal(self):
        """Unpacks the current goal from the list and sends it."""
        if self.goal_index >= len(self.goals):
            self.get_logger().info("All goals completed successfully!")
            self.shutdown_node()
            return

        # Get current target
        x, y, yaw = self.goals[self.goal_index]
        self.get_logger().info(f"--- Processing Goal {self.goal_index + 1}/{len(self.goals)} ---")
        self.send_goal(x, y, yaw)

    def send_goal(self, x, y, yaw):
        # Create the goal message
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
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f'Dist remaining: {feedback.distance_remaining:.2f} m',
            throttle_duration_sec=3.0
        )

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Goal {self.goal_index + 1} SUCCEEDED.')
            
            # Move index to next goal
            self.goal_index += 1
            
            # CHECK IF WE NEED TO WAIT
            if self.goal_index < len(self.goals):
                self.get_logger().info("Waiting 5 seconds before next goal...")
                # Use a ROS Timer instead of time.sleep to avoid blocking the node
                self.timer = self.create_timer(5.0, self.timer_callback)
            else:
                self.shutdown_node()
        else:
            self.get_logger().error(f'Goal failed with status: {status}. Stopping.')
            self.shutdown_node()

    def timer_callback(self):
        """Called after the 5-second wait."""
        self.timer.cancel()  # Stop the timer so it doesn't fire again
        self.get_logger().info("Wait complete. Sending next goal.")
        self.send_next_goal()

    def shutdown_node(self):
        self.get_logger().info('Shutting down node.')
        # Small delay to allow logs to flush
        time.sleep(1)
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)

    # --- DEFINE YOUR LIST OF GOALS HERE ---
    # Format: [(x1, y1, yaw1), (x2, y2, yaw2)]
    
    goal_list = [
        (0.06, -0.42, 90),   # Goal 1
        (0.89, 0.88, 90),      # Goal 2
        (-3.47, -3.79, 90.0),
        (-2.49, -1.36, -180.0),
        (-3.62, -1.36, -180.0) 
    ]
    # --------------------------------------

    action_client_node = NavGoalSender(goal_list)

    try:
        rclpy.spin(action_client_node)
    except KeyboardInterrupt:
        action_client_node.get_logger().info('Keyboard interrupt.')
    except Exception as e: # Catch generic errors safely
        pass
    finally:
        # Check if already shutdown to avoid errors
        if rclpy.ok():
            action_client_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()