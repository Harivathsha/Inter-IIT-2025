#!/usr/bin/env python3
"""
Combined Script: Dual Webcam QR Scanner & Data Cleaner
1. Runs dual camera QR detection (opencv, zxingcpp).
2. Logs to specific directory: ~/dec4_night/articubot_one-new_gazebo/src/qr_scanner/logged_data.csv
3. On exit, automatically removes duplicates and saves to cleaned_data.csv in the same folder.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configuration ---
# The specific folder requested
TARGET_DIRECTORY = os.path.expanduser("~/dec4_night/articubot_one-new_gazebo/src/qr_scanner")

class DualCameraQR:
    def __init__(self, webcam_id_primary=6, webcam_id_secondary=9, csv_path="logged_data.csv", show_windows=True):
        self.webcam_id_primary = int(webcam_id_primary)
        self.webcam_id_secondary = int(webcam_id_secondary)
        self.csv_filename = os.path.expanduser(csv_path)
        self.show_windows = bool(show_windows)

        self.cap_primary = None
        self.cap_secondary = None

        self._setup_csv()
        self._init_cameras()

    def _init_cameras(self):
        self.cap_primary = self._initialize_webcam(self.webcam_id_primary, "Primary")
        self.cap_secondary = self._initialize_webcam(self.webcam_id_secondary, "Secondary")

    def _initialize_webcam(self, camera_id, name):
        cap = cv2.VideoCapture(f"/dev/video{camera_id}")
        if not cap.isOpened():
            logging.error(f"Could not open {name} Webcam (Index {camera_id})")
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        logging.info(f"{name} Webcam initialized on index {camera_id}")
        return cap

    def _setup_csv(self):
        # Ensure directory exists
        folder = os.path.dirname(self.csv_filename)
        if folder and not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
                logging.info(f"Created directory: {folder}")
            except Exception as e:
                logging.error(f"Could not create directory for CSV: {e}")
        
        file_exists = os.path.isfile(self.csv_filename)
        try:
            with open(self.csv_filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Camera_Source", "QR_Text"])
            logging.info(f"Logging raw data to: {self.csv_filename}")
        except Exception as e:
            logging.error(f"CSV Setup Error: {e}")
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
        """
        Process one frame, draw overlays, log and return True if any QR detected.
        """
        if frame is None:
            return False

        results = None
        try:
            results = zxingcpp.read_barcodes(frame)
        except Exception:
            # if raw frame fails, try after preprocessing
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
                try:
                    # r.position might be None for some barcode results; guard accordingly
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
                        # fallback annotate top-left corner
                        cv2.putText(frame, r.text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                    logging.info(f"[{source_name}] Found: {r.text}")

                    # Print to stdout (acts like "publish")
                    print(f"QR_DETECTED | {source_name} | {r.text}")

                    # Publish flag -> print line
                    print("QR_FLAG:1")

                    # Log to CSV
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
                            csv.writer(f).writerow([current_time, source_name, r.text])
                    except Exception as e:
                        logging.error(f"CSV write error: {e}")

                except Exception as e:
                    logging.error(f"Processing Error for {source_name}: {e}")

        # show frame if requested
        if self.show_windows:
            cv2.imshow(f"{source_name} Feed", frame)

        return detected_this_frame

    def run(self):
        logging.info("Starting main loop. Press 'q' in any window or Ctrl+C in terminal to quit.")
        try:
            while True:
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
                    # Print 0 once per loop when nothing detected
                    print("QR_FLAG:0")

                # cv2 wait and key handling
                if self.show_windows:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logging.info("Quit key pressed.")
                        break
                else:
                    # small sleep to avoid busy loop when not showing windows
                    time.sleep(0.01)

        except KeyboardInterrupt:
            logging.info("Interrupted by user (KeyboardInterrupt).")
        finally:
            self.cleanup()

    def cleanup(self):
        logging.info("Cleaning up resources.")
        try:
            if self.cap_primary and self.cap_primary.isOpened():
                logging.info("Releasing Primary Camera.")
                self.cap_primary.release()
        except Exception:
            pass

        try:
            if self.cap_secondary and self.cap_secondary.isOpened():
                logging.info("Releasing Secondary Camera.")
                self.cap_secondary.release()
        except Exception:
            pass

        if self.show_windows:
            cv2.destroyAllWindows()

        logging.info("Scanner shutdown complete.")


# --- Cleaning Function ---

def remove_duplicate_qr_entries(input_filename, output_filename, key_column='QR_Text'):
    """
    Reads a CSV file, removes duplicate rows based on the specified key column,
    and saves the unique entries to a new CSV file.
    """
    logging.info("--- Starting Data Cleanup ---")
    if not os.path.exists(input_filename):
        logging.error(f"Error: Input file '{input_filename}' not found. Cannot clean.")
        return

    try:
        # 1. Read the CSV into a pandas DataFrame
        df = pd.read_csv(input_filename)
        logging.info(f"Original file loaded. Total rows: {len(df)}")

        # 2. Check for the required column
        if key_column not in df.columns:
            logging.error(f"Error: Column '{key_column}' not found. Available: {list(df.columns)}")
            return

        # 3. Remove duplicates
        # 'subset' specifies the column(s) to check for duplicates.
        # 'keep="first"' ensures the first occurrence of a duplicate row is kept.
        df_cleaned = df.drop_duplicates(subset=[key_column], keep='first')

        # 4. Save the de-duplicated data to the new file
        df_cleaned.to_csv(output_filename, index=False)
        logging.info(f"Cleanup complete. Unique entries: {len(df_cleaned)}")
        logging.info(f"Saved cleaned data to: {output_filename}")

    except Exception as e:
        logging.error(f"An unexpected error occurred during cleanup: {e}")


# --- Main Execution ---

def parse_args():
    parser = argparse.ArgumentParser(description="Standalone Dual Webcam QR scanner with Auto-Cleaning.")
    parser.add_argument("--primary", "-p", type=int, default=4, help="Primary webcam index (default: 4)")
    parser.add_argument("--secondary", "-s", type=int, default=2, help="Secondary webcam index (default: 2)")
    parser.add_argument("--no-window", action="store_true", help="Do not show camera windows (headless mode)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Define paths based on the requested directory
    raw_csv_path = os.path.join(TARGET_DIRECTORY, "logged_data.csv")
    cleaned_csv_path = os.path.join(TARGET_DIRECTORY, "cleaned_data.csv")

    logging.info(f"Target Directory: {TARGET_DIRECTORY}")

    # 1. Initialize and Run Scanner
    scanner = DualCameraQR(
        webcam_id_primary=args.primary,
        webcam_id_secondary=args.secondary,
        csv_path=raw_csv_path,
        show_windows=not args.no_window
    )
    
    # This blocks until the user presses 'q' or Ctrl+C
    scanner.run()

    # 2. Run Cleanup automatically after scanner exits
    print("\n")
    logging.info("Scanner stopped. Processing CSV data...")
    remove_duplicate_qr_entries(raw_csv_path, cleaned_csv_path)

if __name__ == "__main__":
    main()