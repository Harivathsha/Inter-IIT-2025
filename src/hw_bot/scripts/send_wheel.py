#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import subprocess
import time
import serial


# ======================= USER CONFIG =======================

# Serial config (ESP32)
SERIAL_PORT = "/dev/ttyUSB1"   # change if needed
BAUD_RATE = 115200

# The message we expect back from the ESP32 to confirm the action is done
ESP32_ACK_MSG = "reached"

# List of waypoints in the MAP frame
# x [m], y [m], yaw_deg [deg], do_action [string or False]
# - If do_action = "m100": sends "m100" to ESP32 and waits for "reached"
# - If do_action = False: no ESP32 command at that waypoint
WAYPOINTS = [
    # Example: Move to point 1, no action
    {"x": 0.1, "y": 0.0, "yaw_deg": 110.0, "do_action": False},
    
    # Example: Move to point 2, send "m100" and wait for "reached"
    {"x": 0.2, "y": 0.0, "yaw_deg": 220.0, "do_action": "m100"},
    
    # Example: Move to point 3, send "m200" (or any other string)
    {"x": 0.3, "y": 0.0, "yaw_deg": 330.0, "do_action": "m200"},
    
    # Example: Move to point 4, no action
    {"x": 0.4, "y": 0.0, "yaw_deg": 440.0, "do_action": False},
]

# How long to wait for ESP32 to send back "reached"
ESP32_ACK_TIMEOUT = 30.0

# ===========================================================


def build_goal_argument(x: float, y: float, yaw_deg: float) -> str:
    """
    Build the YAML argument string for `ros2 action send_goal`.
    """
    yaw_rad = math.radians(yaw_deg)
    qz = math.sin(yaw_rad / 2.0)
    qw = math.cos(yaw_rad / 2.0)

    goal_yaml = (
        "{pose: {"
        "header: {frame_id: map}, "
        "pose: {"
        f"position: {{x: {x:.3f}, y: {y:.3f}, z: 0.0}}, "
        f"orientation: {{x: 0.0, y: 0.0, z: {qz:.6f}, w: {qw:.6f}}}"
        "}"
        "}"
        "}"
    )
    return goal_yaml


def send_nav_goal_cli(x: float, y: float, yaw_deg: float) -> bool:
    """
    Call `ros2 action send_goal` and block until finished.
    """
    goal_arg = build_goal_argument(x, y, yaw_deg)

    cmd = [
        "ros2", "action", "send_goal",
        "/navigate_to_pose",
        "nav2_msgs/action/NavigateToPose",
        goal_arg,
        "--feedback"
    ]

    print("\n==================================================")
    print(f"Sending Nav2 goal via CLI: x={x:.3f}, y={y:.3f}, yaw={yaw_deg:.1f} deg")
    print("Command:")
    print("  " + " ".join(cmd))
    print("==================================================\n")

    # Run the CLI command and wait for it to complete
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.stdout:
        print("---- ros2 action send_goal STDOUT ----")
        print(result.stdout.strip())
        print("---- END STDOUT ----\n")

    if result.stderr:
        print("---- ros2 action send_goal STDERR ----")
        print(result.stderr.strip())
        print("---- END STDERR ----\n")

    if result.returncode != 0:
        print(f"[ERROR] send_goal command failed with return code {result.returncode}")
        return False

    print("[INFO] Nav2 CLI goal finished.")
    return True


def send_and_wait_for_ack(ser: serial.Serial, command: str, expected: str,
                          timeout: float = ESP32_ACK_TIMEOUT) -> bool:
    """
    Send 'command' string to ESP32 and wait until 'expected' line is received.
    """
    print(f"[ESP32] Sending command: '{command}', waiting for ack: '{expected}'")

    try:
        # Clear any old data in buffer
        ser.reset_input_buffer()
        # Send command (e.g., "m100")
        ser.write(command.encode("utf-8"))
    except Exception as e:
        print(f"[ESP32] Error writing to serial: {e}")
        return False

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            if ser.in_waiting > 0:
                raw = ser.readline()
                if not raw:
                    continue
                try:
                    line = raw.decode("utf-8", errors="ignore").strip()
                except UnicodeDecodeError:
                    continue

                if line:
                    print(f"[ESP32] Received: '{line}'")

                # Check if the received line matches "reached"
                if line == expected:
                    print(f"[ESP32] SUCCESS: Got expected ack: '{expected}'")
                    return True

        except Exception as e:
            print(f"[ESP32] Serial read error: {e}")
            return False

        # Small sleep to avoid busy loop
        time.sleep(0.05)

    print(f"[ESP32] Timeout ({timeout}s) waiting for '{expected}'")
    return False


def main():
    # ---- Open serial port to ESP32 ----
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.reset_input_buffer()
        print(f"[ESP32] Connected to {SERIAL_PORT} @ {BAUD_RATE} baud")
    except Exception as e:
        print(f"[ESP32] Could not open serial port ({SERIAL_PORT}): {e}")
        print("[ESP32] Continuing WITHOUT ESP32 actions.")
        ser = None

    # ---- Go through all waypoints ----
    for idx, wp in enumerate(WAYPOINTS, start=1):
        x = wp["x"]
        y = wp["y"]
        yaw_deg = wp["yaw_deg"]
        
        # Determine action command (string or False)
        action_cmd = wp.get("do_action", False)

        print("\n==================================================")
        print(f"WAYPOINT {idx}/{len(WAYPOINTS)}")
        print(f"Target: x={x:.3f}, y={y:.3f}, yaw={yaw_deg:.1f} deg")
        print(f"Action Command: {action_cmd}")
        print("==================================================\n")

        # 1) Send navigation goal via CLI
        ok = send_nav_goal_cli(x, y, yaw_deg)
        if not ok:
            print("[MAIN] Navigation failed. Stopping sequence.")
            break

        print(f"[MAIN] Nav2 reports goal {idx} is finished.")

        # 2) If do_action is a string, send it to ESP32
        if action_cmd and isinstance(action_cmd, str):
            if ser is not None:
                # Send the string (e.g., "m100") and wait for "reached"
                success = send_and_wait_for_ack(ser, action_cmd, ESP32_ACK_MSG)
                if not success:
                    print("[MAIN] ESP32 did not respond with 'reached'. Stopping sequence.")
                    break
            else:
                print(f"[MAIN] Action '{action_cmd}' required but serial not connected.")
        else:
            # If do_action is False (or None, or not a string)
            print("[MAIN] No ESP32 action required for this waypoint.")

        # 3) Small delay between waypoints
        time.sleep(2.0)

    print("\n[MAIN] Navigation sequence finished.")

    if ser is not None:
        try:
            ser.close()
        except Exception:
            pass
        print("[ESP32] Serial port closed.")


if __name__ == "__main__":
    main()