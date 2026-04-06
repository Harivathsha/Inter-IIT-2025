#!/usr/bin/env python3
"""
Combined Script: Dual Webcam QR Scanner & Data Cleaner with ROS 2 Integration
1. Runs dual camera QR detection (opencv, zxingcpp).
2. Subscribes to /odom for Position (X, Y).
3. Subscribes to /cmd_vel to ensure robot is stopped before saving.
4. Logs to: ~/dec4_night/articubot_one-new_gazebo/src/qr_scanner/logged_data.csv
5. On exit, automatically removes duplicates.
"""

import argparse
import csv
import os
import sys
from datetime import datetime
import time
import logging

# Vision imports
import cv2
import numpy as np
import zxingcpp

# Data cleaning imports
import pandas as pd

# ROS 2 Imports
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configuration ---
TARGET_DIRECTORY = os.path.expanduser("~/dec4_night/articubot_one-new_gazebo/src/qr_scanner")

class DualCameraQRNode(Node):
    def __init__(self, webcam_id_primary=6, webcam_id_secondary=9, csv_path="logged_data.csv", show_windows=True):
        super().__init__('dual_camera_qr_node')
        
        # --- ROS 2 Setup ---
        # Subscribe to Odom to get X, Y
        self.subscription_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10)
        
        # Subscribe to Cmd_vel to check if moving
        self.subscription_cmd = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10)

        # State Variables
        self.current_x = 0.0
        self.current_y = 0.0
        self.is_robot_stopped = True # Default to True until we receive a command saying otherwise
        
        # --- Camera & CSV Setup ---
        self.webcam_id_primary = int(webcam_id_primary)
        self.webcam_id_secondary = int(webcam_id_secondary)
        self.csv_filename = os.path.expanduser(csv_path)
        self.show_windows = bool(show_windows)

        self.cap_primary = None
        self.cap_secondary = None

        self._setup_csv()
        self._init_cameras()

    # --- ROS 2 Callbacks ---
    def odom_callback(self, msg):
        """Updates robot position from Odometry"""
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y

    def cmd_vel_callback(self, msg):
        """Checks if the robot is effectively stopped"""
        # We consider the robot stopped if linear X and angular Z are very close to 0
        linear_stopped = abs(msg.linear.x) < 0.001
        angular_stopped = abs(msg.angular.z) < 0.001
        
        if linear_stopped and angular_stopped:
            self.is_robot_stopped = True
        else:
            self.is_robot_stopped = False

    # --- Camera & Processing Methods ---
    def _init_cameras(self):
        self.cap_primary = self._initialize_webcam(self.webcam_id_primary, "Primary")
        self.cap_secondary = self._initialize_webcam(self.webcam_id_secondary, "Secondary")

    def _initialize_webcam(self, camera_id, name):
        try:
            cap = cv2.VideoCapture(f"/dev/video{camera_id}")
            if not cap.isOpened():
                self.get_logger().error(f"Could not open {name} Webcam (Index {camera_id})")
                return None
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.get_logger().info(f"{name} Webcam initialized on index {camera_id}")
            return cap
        except Exception as e:
            self.get_logger().error(f"Error initializing camera {camera_id}: {e}")
            return None

    def _setup_csv(self):
        folder = os.path.dirname(self.csv_filename)
        if folder and not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
                self.get_logger().info(f"Created directory: {folder}")
            except Exception as e:
                self.get_logger().error(f"Could not create directory for CSV: {e}")
        
        file_exists = os.path.isfile(self.csv_filename)
        try:
            with open(self.csv_filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    # Updated Header with Position
                    writer.writerow(["Timestamp", "Camera_Source", "QR_Text", "Pos_X", "Pos_Y"])
            self.get_logger().info(f"Logging raw data to: {self.csv_filename}")
        except Exception as e:
            self.get_logger().error(f"CSV Setup Error: {e}")
            sys.exit(1)

    def preprocess_image(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return cv2.convertScaleAbs(binary, alpha=1.5, beta=0)

    def process_and_scan(self, frame, source_name):
        if frame is None:
            return False

        results = None
        try:
            results = zxingcpp.read_barcodes(frame)
        except Exception:
            results = None

        if not results:
            processed = self.preprocess_image(frame)
            try:
                results = zxingcpp.read_barcodes(processed)
            except Exception:
                results = None

        detected_this_frame = False

        if results:
            detected_this_frame = True
            for r in results:
                # Visualization Code
                if hasattr(r, "position") and r.position is not None:
                    pts = np.array([
                        [r.position.top_left.x, r.position.top_left.y],
                        [r.position.top_right.x, r.position.top_right.y],
                        [r.position.bottom_right.x, r.position.bottom_right.y],
                        [r.position.bottom_left.x, r.position.bottom_left.y]
                    ], dtype=np.int32)
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
                    cv2.putText(frame, r.text, (max(pts[0][0], 0), max(pts[0][1] - 10, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, r.text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # --- SAVING LOGIC ---
                # Only save if robot is stopped (cmd_vel is 0)
                if self.is_robot_stopped:
                    self.get_logger().info(f"[{source_name}] Saving: {r.text} at X:{self.current_x:.2f} Y:{self.current_y:.2f}")
                    
                    # Print for external triggers
                    print(f"QR_DETECTED | {source_name} | {r.text}")
                    print("QR_FLAG:1")

                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
                            # Write row with Position data
                            csv.writer(f).writerow([
                                current_time, 
                                source_name, 
                                r.text, 
                                f"{self.current_x:.4f}", 
                                f"{self.current_y:.4f}"
                            ])
                    except Exception as e:
                        self.get_logger().error(f"CSV write error: {e}")
                else:
                    # Optional: Visual indicator that we see a QR but are ignoring it because we are moving
                    cv2.putText(frame, "MOVING - NOT SAVING", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    # self.get_logger().info(f"QR Seen but Robot Moving. Ignored.")

        if self.show_windows:
            cv2.imshow(f"{source_name} Feed", frame)

        return detected_this_frame

    def camera_loop_step(self):
        """Run one iteration of camera capture and processing"""
        qr_found = False

        if self.cap_primary and self.cap_primary.isOpened():
            ret, frame_primary = self.cap_primary.read()
            if ret and self.process_and_scan(frame_primary, "Webcam_Primary"):
                qr_found = True

        if self.cap_secondary and self.cap_secondary.isOpened():
            ret, frame_secondary = self.cap_secondary.read()
            if ret and self.process_and_scan(frame_secondary, "Webcam_Secondary"):
                qr_found = True

        if not qr_found:
            print("QR_FLAG:0")

        if self.show_windows:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                return False # Signal to stop
        return True # Continue

    def cleanup_cameras(self):
        self.get_logger().info("Cleaning up camera resources.")
        try:
            if self.cap_primary: self.cap_primary.release()
            if self.cap_secondary: self.cap_secondary.release()
            cv2.destroyAllWindows()
        except Exception:
            pass


# --- Cleaning Function ---

def remove_duplicate_qr_entries(input_filename, output_filename, key_column='QR_Text'):
    """
    Deduplicates based on QR_Text, keeping the first occurrence (and its position).
    """
    logging.info("--- Starting Data Cleanup ---")
    if not os.path.exists(input_filename):
        logging.error(f"Error: Input file '{input_filename}' not found. Cannot clean.")
        return

    try:
        df = pd.read_csv(input_filename)
        logging.info(f"Original file loaded. Total rows: {len(df)}")

        if key_column not in df.columns:
            logging.error(f"Error: Column '{key_column}' not found. Available: {list(df.columns)}")
            return

        # Deduplicate based on Text, keeping the first one encountered
        df_cleaned = df.drop_duplicates(subset=[key_column], keep='first')

        df_cleaned.to_csv(output_filename, index=False)
        logging.info(f"Cleanup complete. Unique entries: {len(df_cleaned)}")
        logging.info(f"Saved cleaned data to: {output_filename}")

    except Exception as e:
        logging.error(f"An unexpected error occurred during cleanup: {e}")


# --- Main Execution ---

def parse_args():
    parser = argparse.ArgumentParser(description="ROS 2 Dual Webcam QR scanner with Odom Integration.")
    parser.add_argument("--primary", "-p", type=int, default=4, help="Primary webcam index")
    parser.add_argument("--secondary", "-s", type=int, default=2, help="Secondary webcam index")
    parser.add_argument("--no-window", action="store_true", help="Do not show camera windows")
    return parser.parse_args()


def main(args=None):
    rclpy.init(args=args)
    cli_args = parse_args()

    # Define paths
    raw_csv_path = os.path.join(TARGET_DIRECTORY, "logged_data.csv")
    cleaned_csv_path = os.path.join(TARGET_DIRECTORY, "cleaned_data.csv")

    logging.info(f"Target Directory: {TARGET_DIRECTORY}")

    # Initialize ROS Node
    scanner_node = DualCameraQRNode(
        webcam_id_primary=cli_args.primary,
        webcam_id_secondary=cli_args.secondary,
        csv_path=raw_csv_path,
        show_windows=not cli_args.no_window
    )
    
    logging.info("Starting Main Loop...")
    
    try:
        # We need a loop that processes ROS messages AND runs our camera loop
        while rclpy.ok():
            # 1. Process ROS 2 Callbacks (Odom, Cmd_vel) without blocking
            rclpy.spin_once(scanner_node, timeout_sec=0)

            # 2. Run one step of the camera logic
            should_continue = scanner_node.camera_loop_step()
            
            # 3. Check for exit signal from camera loop (user pressed 'q')
            if not should_continue:
                break
            
            # If running headless (no windows), sleep briefly to prevent CPU hogging
            if cli_args.no_window:
                time.sleep(0.01)

    except KeyboardInterrupt:
        logging.info("Interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        # Cleanup Resources
        scanner_node.cleanup_cameras()
        scanner_node.destroy_node()
        rclpy.shutdown()

        # Run CSV Cleanup
        print("\n")
        logging.info("Node stopped. Processing CSV data...")
        remove_duplicate_qr_entries(raw_csv_path, cleaned_csv_path)

if __name__ == "__main__":
    main()