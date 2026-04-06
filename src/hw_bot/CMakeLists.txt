cmake_minimum_required(VERSION 3.8)
project(hw_bot)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(
  DIRECTORY config description launch rviz scripts maps
  DESTINATION share/${PROJECT_NAME}
)
install(PROGRAMS
  scripts/send_goal.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/nav_waypoints_cli_esp32.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/nav2_script.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/hari_script.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/nav2_single_goal.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/nav2_waypoint_with_poses.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
