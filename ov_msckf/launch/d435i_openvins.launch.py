"""
Launch Intel RealSense D435i + OpenVINS (rs_d435i config).

Requires:
  - realsense2_camera (built/installed, e.g. d1robot/realsense workspace)
  - ov_msckf with config/rs_d435i installed (colcon build ov_msckf)

See config/rs_d435i/launch_d435i.example for topic/calibration notes.
"""

import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declare_rs_enable = DeclareLaunchArgument(
        "rs_enable", default_value="true", description="start realsense2_camera"
    )
    declare_ov_enable = DeclareLaunchArgument(
        "ov_enable", default_value="true", description="start OpenVINS"
    )
    declare_rviz = DeclareLaunchArgument(
        "rviz_enable", default_value="false", description="start rviz2"
    )
    declare_namespace = DeclareLaunchArgument(
        "namespace", default_value="ov_msckf", description="OpenVINS namespace"
    )
    declare_verbosity = DeclareLaunchArgument(
        "verbosity", default_value="INFO", description="OpenVINS log level"
    )

    ov_share = get_package_share_directory("ov_msckf")
    config_path = os.path.join(ov_share, "config", "rs_d435i", "estimator_config.yaml")

    openvins_node = Node(
        package="ov_msckf",
        executable="run_subscribe_msckf",
        namespace=LaunchConfiguration("namespace"),
        output="screen",
        condition=IfCondition(LaunchConfiguration("ov_enable")),
        parameters=[
            {"config_path": config_path},
            {"verbosity": LaunchConfiguration("verbosity")},
            {"use_stereo": True},
            {"max_cameras": 2},
            {"save_total_state": False},
            {"publish_pose_stamped": True},
            {"pose_stamped_frame_id": "global"},
        ],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(LaunchConfiguration("rviz_enable")),
        arguments=[
            "-d",
            os.path.join(ov_share, "launch", "display_ros2.rviz"),
            "--ros-args",
            "--log-level",
            "warn",
        ],
    )

    actions = [
        declare_rs_enable,
        declare_ov_enable,
        declare_rviz,
        declare_namespace,
        declare_verbosity,
    ]

    try:
        rs_share = get_package_share_directory("realsense2_camera")
        rs_launch = os.path.join(rs_share, "launch", "rs_launch.py")
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(rs_launch),
                condition=IfCondition(LaunchConfiguration("rs_enable")),
                launch_arguments={
                    "camera_name": "camera",
                    "camera_namespace": "camera",
                    "enable_infra1": "true",
                    "enable_infra2": "true",
                    "enable_sync": "true",
                    "unite_imu_method": "2",
                    "enable_gyro": "true",
                    "enable_accel": "true",
                    # infra/depth must share 640x360; 640x480 depth breaks with infra@360 on D435i
                    "depth_module.infra_profile": "640x360x90",
                    "depth_module.depth_profile": "640x360x30",
                    "pointcloud.enable": "false",
                }.items(),
            ),
        )
    except PackageNotFoundError:
        actions.append(
            LogInfo(
                msg=(
                    "realsense2_camera not found — starting OpenVINS only. "
                    "Run the camera in another terminal: "
                    "ros2 launch realsense2_camera rs_launch.py "
                    "depth_module.infra_profile:=640x360x90 "
                    "depth_module.depth_profile:=640x360x30"
                )
            ),
        )

    actions.extend([openvins_node, rviz_node])
    return LaunchDescription(actions)
