#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple multi-goal navigation script for your real robot using Nav2.

- Uses Nav2 Simple Commander (BasicNavigator)
- Sends a sequence of goal poses in the 'map' frame
- Nav2 handles planning + control, so speeds come from nav2_params_rgbd.yaml
"""

import math
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


def create_pose(x, y, yaw_deg, frame_id="map"):
    """
    Helper: create a PoseStamped in 'frame_id' with (x, y, yaw).

    x, y in meters
    yaw_deg in degrees (robot heading, 0° = +X, 90° = +Y)
    """
    pose = PoseStamped()
    pose.header.frame_id = frame_id

    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.position.z = 0.0

    # Convert yaw (deg) -> quaternion (roll = pitch = 0)
    yaw = math.radians(yaw_deg)
    pose.pose.orientation.x = 0.0
    pose.pose.orientation.y = 0.0
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)

    return pose


def main():
    rclpy.init()

    navigator = BasicNavigator()

    print("[multi_goal_nav] Waiting for Nav2 (bt_navigator + amcl) to become active...")
    # Works with your existing nav2_bringup launch because autostart=true :contentReference[oaicite:2]{index=2}
    navigator.waitUntilNav2Active()
    print("[multi_goal_nav] Nav2 is active ✔")

    # ----------------------------------------------------------------------
    # (OPTIONAL) If you don't use "2D Pose Estimate" in RViz, you can set
    # the AMCL initial pose here.
    #
    # init_pose = create_pose(0.0, 0.0, 0.0)
    # init_pose.header.stamp = navigator.get_clock().now().to_msg()
    # navigator.setInitialPose(init_pose)
    # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    # 1) EDIT THESE WAYPOINTS FOR YOUR MAP
    #    All coordinates must be in the 'map' frame (same as RViz "Map" view)
    #
    #    Example route (dummy numbers, REPLACE with your real ones):
    # ----------------------------------------------------------------------
    waypoints = [
        create_pose(0.0, 0.0,   0.0),   # Start
        create_pose(0.5, 0.0,   0.0),   # Go forward
        create_pose(1.0, 0.0,  0.0),   # Turn and go up
        create_pose(1.5, 0.0, 0.0),   # Come back towards start
    ]
    # ----------------------------------------------------------------------

    n = len(waypoints)
    if n == 0:
        print("[multi_goal_nav] No waypoints defined, nothing to do.")
        navigator.lifecycleShutdown()
        rclpy.shutdown()
        return

    for i, goal in enumerate(waypoints, start=1):
        # Stamp pose with current time
        goal.header.stamp = navigator.get_clock().now().to_msg()

        print(
            f"[multi_goal_nav] Sending goal {i}/{n} -> "
            f"x={goal.pose.position.x:.3f}, "
            f"y={goal.pose.position.y:.3f}"
        )

        # This uses the NavigateToPose action under the hood
        # (same as clicking Nav2 Goal in RViz). :contentReference[oaicite:3]{index=3}
        navigator.goToPose(goal)

        # Wait until the task is done, while optionally watching feedback
        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            if feedback is not None and hasattr(feedback, "distance_remaining"):
                # 'distance_remaining' is in meters
                print(
                    f"   -> remaining: {feedback.distance_remaining:.2f} m",
                    end="\r",
                )
            time.sleep(0.1)

        result = navigator.getResult()

        print()  # newline after the \r prints
        if result == TaskResult.SUCCEEDED:
            print(f"[multi_goal_nav] ✅ Reached waypoint {i}/{n}")
        elif result == TaskResult.CANCELED:
            print(f"[multi_goal_nav] ⚠ Goal {i}/{n} was canceled, stopping sequence.")
            break
        elif result == TaskResult.FAILED:
            print(f"[multi_goal_nav] ❌ Failed to reach waypoint {i}/{n}, stopping.")
            break
        else:
            print(f"[multi_goal_nav] Unknown result for waypoint {i}/{n}: {result}")
            break

    print("[multi_goal_nav] Shutting down Nav2 lifecycle from script.")
    navigator.lifecycleShutdown()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
