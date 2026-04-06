# 📦 Autonomous Warehouse Inventory Rover

[![ROS 2](https://img.shields.io/badge/ROS_2-Humble-34a853?style=flat&logo=ros)](https://docs.ros.org/en/humble/)
[![Gazebo](https://img.shields.io/badge/Simulator-Gazebo_Ignition-ff6600?style=flat)](https://gazebosim.org/)
[![Hardware](https://img.shields.io/badge/Compute-Jetson_AGX_Xavier-76B900?style=flat&logo=nvidia)](#)
[![Docker](https://img.shields.io/badge/Containerized-Docker-2496ED?style=flat&logo=docker)](#)
[![Ubuntu](https://img.shields.io/badge/OS-Ubuntu_22.04-E95420?style=flat&logo=ubuntu)](#)

A physical, industrial-grade autonomous mobile robot designed for dynamic warehouse environments. This project features a complete hardware-software stack, combining 3D visual SLAM, custom embedded ESP controllers via `ros2_control`, a dynamic Z-axis scanning lift, and a GPU-accelerated computer vision pipeline for highly reliable QR code inventory tracking.

Developed and validated through rigorous Gazebo Ignition simulations before successful deployment in a physical testing arena.

---

## ✨ Core System Features

### 🗺️ 3D Mapping & Navigation (RTAB-Map & Nav2)
* **Visual SLAM:** Utilizes RTAB-Map with RGB-D input to fuse odometry and visual features into a graph-based representation, incorporating loop-closure to eliminate drift.
* **Dynamic Path Planning:** * **Global Costmap:** A* routing for long-distance warehouse navigation.
  * **Local Costmap:** Voxel-based 3D geometry tracking to avoid overhanging shelves and dynamic obstacles.
  * **Trajectory Smoothing:** Dynamically feasible reference trajectories enforcing strict acceleration/speed limits for tight spaces.

### 👁️ Two-Stage Scanning Vision Pipeline
Engineered to handle noise, uneven warehouse lighting, and motion blur using 640x480 RGB camera feeds.
* **Stage 1 (Direct):** Fast, raw-frame decoding via **ZXing-CPP**.
* **Stage 2 (Fallback Preprocessing):** If direct decoding fails, the system applies grayscale conversion, 3x3 Gaussian blur, adaptive thresholding, and contrast scaling (α = 1.5) before re-submitting to the decoder with homography perspective correction.

### ⚙️ Hardware Integration & `ros2_control`
* **Middleware:** Powered by **Cyclone DDS** for deterministic, low-latency publish-subscribe communication.
* **`diff_drive_esp` Plugin:** A custom hardware interface translating ROS 2 `cmd_vel` topics into UART commands for an ESP-based motor controller, processing closed-loop encoder feedback for precise odometry.
* **`z_axis_esp` Plugin:** Controls a vertical lift mechanism via local PID, moving the camera payload to dynamically calculated heights for multi-level shelf scanning.

### 📱 Human-Machine Interface (HMI)
* **Mobile Application:** Provides remote supervision, live video telemetry, inventory scan readouts, and manual override capabilities.
* **Capacitive Touchscreen:** Onboard display for real-time diagnostics (voltage, current, thermals) and local fallback control.

---

## 🛡️ Industrial Fail-Safes & Safety

* **Hardware Clamping:** Firmware-level outlier detection discards out-of-bounds velocity commands before they reach the motors.
* **Dynamic E-Stop:** Software triggers an immediate emergency stop if unmapped obstacles suddenly appear in the local costmap.
* **Perception Watchdog:** If the camera feed crashes, the respective ROS 2 node is automatically killed and restarted while the rover safely maintains localization.
* **Human-in-the-Loop:** Instant manual override and halt capabilities via the mobile application over the DDS network.

---

## 🏗️ System Architecture & Deployment

The entire software stack is fully encapsulated using **Docker**, ensuring consistency from simulation to physical deployment.

* **Target Compute:** NVIDIA Jetson AGX Xavier.
* **Hardware Acceleration:** The NVIDIA Docker runtime exposes CUDA, cuDNN, and TensorRT to the perception and planning pipelines.
* **Modular Containers:** Navigation, perception, and hardware control run in isolated, easily updatable containers to prevent dependency conflicts.

---

## 🚀 Installation & Build

### Prerequisites
* Ubuntu 22.04 LTS
* ROS 2 Humble Hawksbill
* Docker & NVIDIA Container Toolkit (for physical deployment)
* Gazebo Ignition (for simulation)

### Workspace Setup
```bash
# Source ROS 2
source /opt/ros/humble/setup.bash

# Clone the repository
mkdir -p ~/rover_ws/src && cd ~/rover_ws/src
git clone <repository_url> .

# Install dependencies
cd ~/rover_ws
rosdep update![IMG20251206213609](https://github.com/user-attachments/assets/7c750e38-6008-41ce-b655-7a5d4cfc8406)

rosdep install --from-paths src --ignore-src -r -y

# Build the workspace
colcon build --symlink-install

```
<img width="1026" height="558" alt="Screenshot from 2026-03-26 23-19-12" src="https://github.com/user-attachments/assets/f1156a39-781c-40f1-bdcf-57ad62cb48ce" />


https://github.com/user-attachments/assets/205d257a-411e-4a54-89f3-afe97f68ca67





