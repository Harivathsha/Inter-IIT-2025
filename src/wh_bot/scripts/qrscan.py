#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

import cv2
from cv_bridge import CvBridge
import numpy as np
import zxingcpp
import csv
import os


class QRScannerNode(Node):
    def __init__(self):
        super().__init__("qr_scanner_node")

        # ROS image subscriber (RealSense color topic)
        self.subscription = self.create_subscription(
            Image,
            "/camera/color/image_raw",
            self.image_callback,
            10
        )

        # Publisher for decoded QR text
        self.publisher_ = self.create_publisher(String, "/qr_scanner/data", 10)

        self.bridge = CvBridge()

        # CSV setup
        self.csv_filename = "qr_scanned_data.csv"
        file_exists = os.path.isfile(self.csv_filename)

        with open(self.csv_filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["QR_Text"])

        self.get_logger().info("QR Scanner Node started.")

    # ------------------ PREPROCESSING FUNCTION ------------------
    def preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        binary = cv2.convertScaleAbs(binary, alpha=1.5, beta=0)
        return binary

    # ------------------ IMAGE CALLBACK ------------------
    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Step 1: Try direct decode
        results = zxingcpp.read_barcodes(frame)

        # Step 2: Try preprocessed version
        if not results:
            processed = self.preprocess(frame)
            results = zxingcpp.read_barcodes(processed)

        # Step 3: Visualization + Logging
        if results:
            for r in results:
                self.get_logger().info(f"QR Data: {r.text}")

                # ---- Publish decoded data ----
                msg_out = String()
                msg_out.data = r.text
                self.publisher_.publish(msg_out)

                # ---- Save to CSV ----
                with open(self.csv_filename, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([r.text])


def main(args=None):
    rclpy.init(args=args)
    node = QRScannerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
