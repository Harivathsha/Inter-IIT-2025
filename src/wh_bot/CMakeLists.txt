cmake_minimum_required(VERSION 3.8)
project(wh_bot)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)

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


install(DIRECTORY
  config
  launch
  worlds
  description
  meshes
  rviz
  maps
  scripts
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/lift_controller.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME lift_controller
)

install(PROGRAMS
  scripts/take_picture.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME take_picture
)

install(PROGRAMS
  scripts/send_goal.py
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/lift_bridge.py
  DESTINATION lib/${PROJECT_NAME}
)


ament_package()
