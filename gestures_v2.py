#!/usr/bin/env python3
"""CRANE+ V2 / ROS 2 Humble / Gazebo: greeting, polite, and rest.

Use in the same ROS 2 environment as lecture #5:
    python3 gestures_v2.py greeting
    python3 gestures_v2.py polite
    python3 gestures_v2.py rest

For Gazebo simulation only. This sends joint-space goals; it does not plan
collision-free paths and does not read back or verify actual joint motion.
"""

import argparse
import time

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

ARM_TOPIC = "/crane_plus_arm_controller/joint_trajectory"
GRIPPER_TOPIC = "/crane_plus_gripper_controller/joint_trajectory"
ARM_JOINTS = [
    "crane_plus_joint1",
    "crane_plus_joint2",
    "crane_plus_joint3",
    "crane_plus_joint4",
]
GRIPPER_JOINT = "crane_plus_joint_hand"

VERTICAL = (0.0, 0.0, 0.0, 0.0)
# Official CRANE+ V2 SRDF home pose, not a safety-verified trajectory.
OFFICIAL_HOME = (0.0, -1.16, -2.01, -0.73)
REST_FRACTION = 0.4  # Tested by the user in the lecture's Gazebo scene.
REST_POSE = tuple(round(angle * REST_FRACTION, 4) for angle in OFFICIAL_HOME)

# Same angles as the physicalai_teleop lecture package.
GRIPPER_OPEN = -0.5236
GRIPPER_CLOSE = 0.1745

# Each step is: (kind, seconds, target, description).
# kind == "arm" -> four joint positions in radians
# kind == "gripper" -> one hand joint position in radians
# kind == "pause" -> target ignored
GREETING = [
    ("arm", 2.0, VERTICAL, "正面に戻る"),
    ("gripper", 1.0, GRIPPER_OPEN, "グリッパーを開く"),
]
# Alternate left/right facing and open/close three times.
for side, base_angle in (("左", 0.30), ("右", -0.30), ("左", 0.30)):
    GREETING.extend([
        ("arm", 1.3, (base_angle, 0.0, 0.0, 0.0), f"{side}を向く"),
        ("gripper", 0.9, GRIPPER_CLOSE, "パチッ：グリッパーを閉じる"),
        ("gripper", 0.9, GRIPPER_OPEN, "グリッパーを開く"),
    ])
GREETING.extend([
    ("arm", 1.4, VERTICAL, "正面へ戻る"),
    ("arm", 2.0, (0.0, 0.15, 0.0, 0.0), "軽く会釈"),
    ("arm", 2.0, VERTICAL, "顔を上げる"),
])

GESTURES = {
    "greeting": GREETING,
    "polite": [
        ("arm", 2.5, VERTICAL, "直立に戻る"),
        ("arm", 3.0, (0.0, 0.4, 0.0, 0.0), "ゆっくり深くお辞儀"),
        ("arm", 3.0, VERTICAL, "ゆっくり上体を戻す"),
    ],
    "rest": [
        ("arm", 2.5, VERTICAL, "直立姿勢へ戻す"),
        ("gripper", 1.0, GRIPPER_OPEN, "グリッパーを開く"),
        ("arm", 5.0, REST_POSE, "ゆっくり待機姿勢へ (公式homeの40%)"),
        ("gripper", 1.5, GRIPPER_CLOSE, "ゆっくりグリッパーを閉じる"),
        ("pause", 3.0, None, "静かに待機する"),
    ],
}


def publish_joint_goal(publisher, names, positions, duration):
    msg = JointTrajectory()
    msg.joint_names = list(names)
    point = JointTrajectoryPoint()
    point.positions = [float(x) for x in positions]
    duration_ns = int(round(duration * 1_000_000_000))
    point.time_from_start.sec, point.time_from_start.nanosec = divmod(
        duration_ns, 1_000_000_000
    )
    msg.points = [point]
    publisher.publish(msg)
    # Wait for the planned time; this is NOT physical success verification.
    time.sleep(duration + 0.35)


def wait_for_subscriber(publisher, topic, timeout=6.0):
    deadline = time.monotonic() + timeout
    while publisher.get_subscription_count() == 0:
        if time.monotonic() >= deadline:
            raise RuntimeError(f"ROS 2コントローラーに接続できません: {topic}")
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description="CRANE+ V2 gestures in Gazebo")
    parser.add_argument("gesture", choices=sorted(GESTURES))
    args = parser.parse_args()

    rclpy.init()
    node = Node("pai_gestures_v2")
    try:
        arm_pub = node.create_publisher(JointTrajectory, ARM_TOPIC, 10)
        hand_pub = node.create_publisher(JointTrajectory, GRIPPER_TOPIC, 10)
        wait_for_subscriber(arm_pub, ARM_TOPIC)
        wait_for_subscriber(hand_pub, GRIPPER_TOPIC)

        print(f"動作開始: {args.gesture}", flush=True)
        for index, (kind, seconds, target, label) in enumerate(GESTURES[args.gesture], 1):
            print(f"{index:02d}. {label}", flush=True)
            if kind == "arm":
                publish_joint_goal(arm_pub, ARM_JOINTS, target, seconds)
            elif kind == "gripper":
                publish_joint_goal(hand_pub, [GRIPPER_JOINT], [target], seconds)
            elif kind == "pause":
                time.sleep(seconds)
            else:
                raise ValueError(f"Unknown gesture step: {kind}")
        print("指令送信が完了。Gazeboで実際の動作を確認してください。", flush=True)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
