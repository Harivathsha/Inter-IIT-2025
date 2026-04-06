#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped


class Nav2SingleGoalClient(Node):
    def __init__(self):
        super().__init__('nav2_single_goal_client')

        # Action client to the Nav2 navigate_to_pose action server
        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    # Helper to build a PoseStamped in the "map" frame
    def make_pose(self, x, y, yaw_rad):
        pose = PoseStamped()
        pose.header.frame_id = 'map'  # Must match bt_navigator.global_frame
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        # 2D yaw → quaternion (z, w only)
        qz = math.sin(yaw_rad / 2.0)
        qw = math.cos(yaw_rad / 2.0)
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        return pose

    def send_goal(self, pose: PoseStamped):
        self.get_logger().info('Waiting for "navigate_to_pose" action server...')
        self._client.wait_for_server()

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.get_logger().info(
            f'Sending goal: x={pose.pose.position.x:.3f}, '
            f'y={pose.pose.position.y:.3f}'
        )

        send_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_future.add_done_callback(self.goal_response_callback)

    # Called while robot is moving
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f'[NavigateToPose] distance_remaining = '
            f'{feedback.distance_remaining:.3f} m'
        )

    # Called once the action server accepts / rejects the goal
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal was REJECTED by Nav2')
            return

        self.get_logger().info('Goal accepted, waiting for result...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    # Called when navigation finishes (success, aborted, etc.)
    def result_callback(self, future):
        result = future.result().result
        status = future.result().status
        self.get_logger().info(
            f'[NavigateToPose] finished with status={status}, result={result}'
        )

        self.get_logger().info('Shutting down Nav2SingleGoalClient node.')
        self.destroy_node()
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = Nav2SingleGoalClient()

    # >>>>>>> EDIT THESE VALUES <<<<<<<
    # Example: go to (0.1, 0.0) with yaw = 0 rad
    goal_pose = node.make_pose(x=1.0, y=0.0, yaw_rad=0.0)

    node.send_goal(goal_pose)
    rclpy.spin(node)


if __name__ == '__main__':
    main()
