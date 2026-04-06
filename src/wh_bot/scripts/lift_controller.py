#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class LiftController(Node):
    def __init__(self):
        super().__init__("lift_controller")

        # Publisher
        self.publisher_ = self.create_publisher(
            JointTrajectory, "/torso_controller/joint_trajectory", 10
        )

        self.target_height = 0.8     # meters
        self.lower_height = 0.0      # starting position
        self.move_time = 3.0         # seconds to move up or down
        self.wait_time = 20.0        # seconds to wait at top

        # Step 1: schedule the upward movement
        self.timer = self.create_timer(1.0, self.move_up)
        self.get_logger().info("Lift controller initialized.")

    # ---------------------- MOVE UP ----------------------
    def move_up(self):
        self.timer.cancel()  # run only once

        self.get_logger().info(f"Moving UP to {self.target_height} m")

        msg = JointTrajectory()
        msg.joint_names = ["joint_lift_1", "joint_lift_2"]

        point = JointTrajectoryPoint()
        point.positions = [self.target_height, self.target_height]
        point.time_from_start.sec = int(self.move_time)

        msg.points.append(point)
        self.publisher_.publish(msg)

        # After reaching top, wait 20 seconds
        self.timer = self.create_timer(self.wait_time, self.move_down)

    # ---------------------- MOVE DOWN ----------------------
    def move_down(self):
        self.timer.cancel()  # run only once

        self.get_logger().info(f"20 seconds completed. Moving DOWN to {self.lower_height} m")

        msg = JointTrajectory()
        msg.joint_names = ["joint_lift_1", "joint_lift_2"]

        point = JointTrajectoryPoint()
        point.positions = [self.lower_height, self.lower_height]
        point.time_from_start.sec = int(self.move_time)

        msg.points.append(point)
        self.publisher_.publish(msg)

        self.get_logger().info("Movement complete. Lift returned to initial position.")

def main(args=None):
    rclpy.init(args=args)
    node = LiftController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
