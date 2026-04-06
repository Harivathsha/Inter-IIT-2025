#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
import serial
import time

class LiftBridge(Node):
    def __init__(self):
        super().__init__('lift_bridge')
        
        # CHANGE THIS TO YOUR ESP32 PORT
        self.serial_port = serial.Serial('/dev/ttyUSB0', 57600, timeout=1) 
        self.get_logger().info("Connected to ESP32 Lift")

        # Subscription: You publish to /lift_target, this sends to ESP32
        self.subscription = self.create_subscription(
            Int32,
            'lift_target',
            self.listener_callback,
            10)

    def listener_callback(self, msg):
        target = msg.data
        command = f"p {target}\n"
        self.serial_port.write(command.encode('utf-8'))
        self.get_logger().info(f'Sent to Lift: {command.strip()}')

def main(args=None):
    rclpy.init(args=args)
    node = LiftBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.serial_port.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()