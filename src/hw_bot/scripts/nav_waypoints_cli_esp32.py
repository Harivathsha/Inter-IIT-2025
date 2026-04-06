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

# List of waypoints in the MAP frame
# x [m], y [m], yaw_deg [deg], do_action [bool]
# - If do_action = True: send "up"/"down" to ESP32 (alternating each time)
# - If do_action = False: no ESP32 command at that waypoint
WAYPOINTS = [
    {"x": 0.1, "y": 0.0, "yaw_deg": 110.0, "do_action": False},
    {"x":0.2, "y": 0.0, "yaw_deg": 220.0, "do_action": False},
    {"x": 0.3, "y": 0.0, "yaw_deg": 330.0, "do_action": False},
    {"x": 0.4, "y": 0.0, "yaw_deg": 440.0, "do_action": False},
    # {"x": 0.24, "y": 7.26, "yaw_deg": 220.0, "do_action": False},
    # {"x": -0.76, "y": 6.44, "yaw_deg": 330.0, "do_action": True},

]

# How long to wait for ESP32 ack ("max_u"/"max_d") in seconds
ESP32_ACK_TIMEOUT = 30.0

# ===========================================================


def build_goal_argument(x: float, y: float, yaw_deg: float) -> str:
    """
    Build the YAML argument string for `ros2 action send_goal`.

    This produces something like:
    {pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.0, z: 0.0},
                                           orientation: {x: 0.0, y: 0.0, z: ..., w: ...}}}}
    """
    yaw_rad = math.radians(yaw_deg)
    qz = math.sin(yaw_rad / 2.0)
    qw = math.cos(yaw_rad / 2.0)

    # Single-line YAML-like dictionary, same structure as your working CLI command
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
    Call `ros2 action send_goal /navigate_to_pose ...` as a subprocess
    and block until the action finishes.
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

    # Show CLI output (useful for debugging)
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

    print("[INFO] Nav2 CLI goal finished (action server returned a result).")
    return True


def send_and_wait_for_ack(ser: serial.Serial, command: str, expected: str,
                          timeout: float = ESP32_ACK_TIMEOUT) -> bool:
    """
    Send 'command' to ESP32 and wait until 'expected' line is received or timeout.
    """
    print(f"[ESP32] Sending command: '{command}', expecting ack: '{expected}'")

    try:
        # Clear any old data
        ser.reset_input_buffer()
        # Send command
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

                if line == expected:
                    print(f"[ESP32] Got expected ack: '{expected}'")
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

    # This toggles: True → send "up"/wait "max_u", False → "down"/"max_d"
    next_is_up = True

    # ---- Go through all waypoints ----
    for idx, wp in enumerate(WAYPOINTS, start=1):
        x = wp["x"]
        y = wp["y"]
        yaw_deg = wp["yaw_deg"]
        do_action = wp.get("do_action", False)

        print("\n==================================================")
        print(f"WAYPOINT {idx}/{len(WAYPOINTS)}")
        print(f"Target: x={x:.3f}, y={y:.3f}, yaw={yaw_deg:.1f} deg, do_action={do_action}")
        print("==================================================\n")

        # 1) Send navigation goal via CLI
        ok = send_nav_goal_cli(x, y, yaw_deg)
        if not ok:
            print("[MAIN] Navigation failed. Stopping sequence.")
            break

        print(f"[MAIN] Nav2 reports goal {idx} is finished.")

        # 2) If needed, talk to ESP32
        if do_action and ser is not None:
            if next_is_up:
                cmd = "up"
                expected = "max_u"
            else:
                cmd = "down"
                expected = "max_d"

            success = send_and_wait_for_ack(ser, cmd, expected)
            if not success:
                print("[MAIN] ESP32 did not respond correctly. Stopping sequence.")
                break

            # Toggle for next action waypoint
            next_is_up = not next_is_up
        else:
            if do_action and ser is None:
                print("[MAIN] do_action=True but no serial connection; skipping ESP32 step.")
            else:
                print("[MAIN] This waypoint does not require ESP32 action.")

        # 3) Small delay between waypoints so everything settles
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
