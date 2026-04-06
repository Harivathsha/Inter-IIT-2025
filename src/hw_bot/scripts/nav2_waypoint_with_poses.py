#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateThroughPoses
from geometry_msgs.msg import PoseStamped


class Nav2WaypointsClient(Node):
    def __init__(self):
        super().__init__('nav2_waypoints_client')

        # Action client to the Nav2 NavigateThroughPoses server
        self._client = ActionClient(self, NavigateThroughPoses, 'navigate_through_poses')

    def make_pose(self, x, y, yaw_rad):
        pose = PoseStamped()
        pose.header.frame_id = 'map'   # same as bt_navigator.global_frame
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        qz = math.sin(yaw_rad / 2.0)
        qw = math.cos(yaw_rad / 2.0)
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        return pose

    def send_waypoints(self, waypoints):
        self.get_logger().info('Waiting for "navigate_through_poses" action server...')
        self._client.wait_for_server()

        # Stamp all at current time
        now = self.get_clock().now().to_msg()
        for p in waypoints:
            p.header.stamp = now
            if not p.header.frame_id:
                p.header.frame_id = 'map'

        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = waypoints
        # goal_msg.behavior_tree = ''  # optional, use Nav2 default BT

        self.get_logger().info(f'Sending {len(waypoints)} waypoints to Nav2...')

        send_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_future.add_done_callback(self.goal_response_callback)

    # Called while going through waypoints
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        x = feedback.current_pose.pose.position.x
        y = feedback.current_pose.pose.position.y
        self.get_logger().info(
            f'[NavigateThroughPoses] currently heading to waypoint '
            f'#{feedback.current_waypoint + 1}, approx pos=({x:.2f}, {y:.2f})'
        )

    # Called when the server accepts / rejects
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Waypoints goal was REJECTED by Nav2')
            return

        self.get_logger().info('Waypoints goal accepted, waiting for result...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    # Called when all waypoints are done / aborted / canceled
    def result_callback(self, future):
        result = future.result().result
        status = future.result().status
        self.get_logger().info(
            f'[NavigateThroughPoses] finished with status={status}, result={result}'
        )
        self.get_logger().info('Shutting down Nav2WaypointsClient node.')
        self.destroy_node()
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = Nav2WaypointsClient()

    # >>>>>>> EDIT YOUR WAYPOINTS HERE <<<<<<<
    # Example square path in map frame (units: meters, yaw in rad)
    waypoints = [
        node.make_pose(0.5, 0.0, 0.0),     # WP1
        node.make_pose(1.0, 0.0, 0.0),    # WP2
        node.make_pose(1.5, 0.0, 0.0),    # WP3
        node.make_pose(2.0, 0.0, 0.0),   # WP4 (back towards start)
    ]

    node.send_waypoints(waypoints)
    rclpy.spin(node)


if __name__ == '__main__':
    main()
