#!/usr/bin/env python3
import rclpy
import cv2
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge # Package to convert ROS images to OpenCV

class ImageSaver(Node):

    def __init__(self):
        super().__init__('image_saver_node')
        
        # Create a CvBridge object
        self.bridge = CvBridge()
        
        # Create a subscriber
        # This will subscribe to the topic from your XACRO file
        self.subscription = self.create_subscription(
            Image,
            '/z_axis_camera_1/image_raw',
            self.image_callback,
            10)
        
        self.get_logger().info('Node started. Waiting for one image on topic...')
        self.image_received = False

    def image_callback(self, msg):
        # We only want to save one image
        if self.image_received:
            return

        self.get_logger().info('Image received!')
        self.image_received = True

        try:
            # Convert the ROS 2 Image message to an OpenCV image
            # The XACRO file specified R8G8B8, which cv_bridge converts to "bgr8"
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')
            return

        # Define the file path to save the image
        file_path = "my_image.jpg"
        
        # Save the OpenCV image to a file
        if cv2.imwrite(file_path, cv_image):
            self.get_logger().info(f'Successfully saved image to {file_path}')
        else:
            self.get_logger().error(f'Failed to save image to {file_path}')

        # Shutdown the node after saving the image
        self.get_logger().info('Shutting down node.')
        self.destroy_node()
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    image_saver = ImageSaver()
    try:
        rclpy.spin(image_saver)
    except SystemExit:
        rclpy.logging.get_logger("Quitting").info('Done.')

if __name__ == '__main__':
    main()