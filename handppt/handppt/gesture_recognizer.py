"""
手势识别模块
基于 21 个手部关键点，识别各类手势：
- 翻页手势：左滑 (swipe_left)、右滑 (swipe_right)
- 模式切换手势：OK 手势（拇指 + 食指捏合）
- 指书翻页：1 指 (one_finger) → 下一页，2 指 (two_fingers) → 上一页
- 扩展：握拳 (fist) → 黑屏切换，竖大拇指 (thumbs_up) → 第一页，5指 (five_fingers) → 最后一页
"""

import math
import time
from collections import deque

import numpy as np

import config
from hand_detector import DetectionResult, HandData, HandLandmark


# MediaPipe 手部关键点索引
class LandmarkIndex:
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class GestureRecognizer:
    """手势识别器"""

    def __init__(self):
        # 用于滑动检测的历史位置（掌心 x 坐标）
        self._palm_x_history = deque(maxlen=5)
        self._prev_palm_x = None
        self._swipe_cooldown_until = 0.0

        # 用于 OK 手势的稳定检测
        self._ok_stable_count = 0
        self._ok_triggered = False  # 避免连续触发

        # 用于指书翻页的稳定检测
        self._finger_stable_frames: dict[str, int] = {
            "one_finger": 0,
            "two_fingers": 0,
        }
        self._finger_triggered: dict[str, bool] = {
            "one_finger": False,
            "two_fingers": False,
        }
        self._finger_cooldown_until = 0.0

        # ---- 新增全局手势 ----
        self._fist_stable_count = 0
        self._fist_triggered = False
        self._thumbs_up_stable_count = 0
        self._thumbs_up_triggered = False
        self._five_fingers_stable_count = 0
        self._five_fingers_triggered = False

        # ---- 三指（食指+中指+无名指）演讲稿切换 ----
        self._three_fingers_stable_count = 0
        self._three_fingers_triggered = False

        # ---- 比心手势（拇指+食指交叉）标记重点页 ----
        self._heart_stable_count = 0
        self._heart_triggered = False
        self._heart_cooldown_until = 0.0

        self._special_cooldown_until = 0.0
        self._last_hand_count = 0   # 用于检测手突然消失再出现

        # 上一次识别到的手势
        self._last_gesture = "none"

    def recognize(self, result: DetectionResult) -> str:
        """
        识别手势，返回手势名称字符串：
        - "swipe_left"    左滑翻页
        - "swipe_right"   右滑翻页
        - "ok_gesture"    OK 手势（切换模式）
        - "one_finger"    伸 1 指 → 下一页
        - "two_fingers"   伸 2 指 → 上一页
        - "fist"          握拳 → 黑屏/恢复
        - "thumbs_up"     竖大拇指 → 跳到第一页
        - "five_fingers"  五指张开 → 跳到最后一页
        - "heart_gesture" 比心手势 → 标记当前页为重点页
        - "three_fingers" 三指 → 切换演讲稿显示
        - "none"          无有效手势
        """
        if result.num_hands == 0:
            self._ok_stable_count = 0
            self._finger_stable_frames["one_finger"] = 0
            self._finger_stable_frames["two_fingers"] = 0
            self._fist_stable_count = 0
            self._thumbs_up_stable_count = 0
            self._five_fingers_stable_count = 0
            self._three_fingers_stable_count = 0
            self._three_fingers_triggered = False
            self._heart_stable_count = 0
            self._heart_triggered = False
            self._last_hand_count = 0
            self._last_gesture = "none"
            return "none"

        hand = result.get_hand(0)
        if hand is None:
            return "none"

        lm = hand.landmarks
        current_time = time.time()

        # ---- 冷却：触发特殊手势后短暂冷却，避免连续触发 ----
        if current_time < self._special_cooldown_until:
            self._last_gesture = "none"
            return "none"

        # 1. 检测 OK 手势（优先级最高）
        if self._detect_ok_gesture(lm):
            self._ok_stable_count += 1
            stable_frames = max(3, int(30 * config.ADAPTIVE_STABILITY_SECONDS))
            if self._ok_stable_count >= stable_frames and not self._ok_triggered:
                self._ok_triggered = True
                self._last_gesture = "ok_gesture"
                return "ok_gesture"
        else:
            self._ok_stable_count = 0
            self._ok_triggered = False

        # 2. 检测数字指法（1 指 / 2 指）
        finger_gesture = self._detect_finger_count(lm, current_time)
        if finger_gesture:
            self._last_gesture = finger_gesture
            return finger_gesture

        # 3. 检测特殊手势：握拳、竖大拇指、五指张开
        special_gesture = self._detect_special_gestures(lm, current_time)
        if special_gesture:
            self._special_cooldown_until = current_time + 2.0  # 2秒冷却
            self._last_gesture = special_gesture
            return special_gesture

        # 4. 检测比心手势（拇指+食指交叉）→ 标记当前页为重点页
        heart_gesture = self._detect_heart_gesture(lm, current_time)
        if heart_gesture:
            self._last_gesture = heart_gesture
            return heart_gesture

        # 5. 检测三指（食指+中指+无名指）→ 切换演讲稿显示
        three_fingers = self._detect_three_fingers(lm, current_time)
        if three_fingers:
            self._last_gesture = three_fingers
            return three_fingers

        # 5. 检测滑动翻页
        if current_time < self._swipe_cooldown_until:
            self._last_gesture = "none"
            return "none"

        gesture = self._detect_swipe(lm)
        if gesture:
            self._swipe_cooldown_until = current_time + config.SWIPE_COOLDOWN_SECONDS
            self._last_gesture = gesture
            return gesture

        self._last_gesture = "none"
        return "none"

    def _detect_ok_gesture(self, lm: list[HandLandmark]) -> bool:
        """
        检测 OK 手势：
        拇指尖与食指尖距离很近（捏合），且中指、无名指、小指伸展开
        """
        thumb_tip = np.array([lm[LandmarkIndex.THUMB_TIP].x, lm[LandmarkIndex.THUMB_TIP].y])
        index_tip = np.array([lm[LandmarkIndex.INDEX_FINGER_TIP].x, lm[LandmarkIndex.INDEX_FINGER_TIP].y])
        distance = np.linalg.norm(thumb_tip - index_tip)

        # 拇指和食指距离小于阈值
        if distance > config.OK_GESTURE_DISTANCE_THRESHOLD / 1000.0:
            return False

        # 检查中指、无名指、小指是否伸展（指尖远离掌心）
        wrist = np.array([lm[LandmarkIndex.WRIST].x, lm[LandmarkIndex.WRIST].y])
        mcp_avg_x = (lm[LandmarkIndex.MIDDLE_FINGER_MCP].x + lm[LandmarkIndex.RING_FINGER_MCP].x + lm[LandmarkIndex.PINKY_MCP].x) / 3
        mcp_avg_y = (lm[LandmarkIndex.MIDDLE_FINGER_MCP].y + lm[LandmarkIndex.RING_FINGER_MCP].y + lm[LandmarkIndex.PINKY_MCP].y) / 3
        mcp_avg = np.array([mcp_avg_x, mcp_avg_y])

        middle_tip = np.array([lm[LandmarkIndex.MIDDLE_FINGER_TIP].x, lm[LandmarkIndex.MIDDLE_FINGER_TIP].y])
        ring_tip = np.array([lm[LandmarkIndex.RING_FINGER_TIP].x, lm[LandmarkIndex.RING_FINGER_TIP].y])
        pinky_tip = np.array([lm[LandmarkIndex.PINKY_TIP].x, lm[LandmarkIndex.PINKY_TIP].y])

        # 三根手指的指尖都应该比指根（MCP）更远离手腕
        dist_middle = np.linalg.norm(middle_tip - wrist)
        dist_ring = np.linalg.norm(ring_tip - wrist)
        dist_pinky = np.linalg.norm(pinky_tip - wrist)
        dist_mcp_avg = np.linalg.norm(mcp_avg - wrist)

        return (dist_middle > dist_mcp_avg * 0.8 and
                dist_ring > dist_mcp_avg * 0.8 and
                dist_pinky > dist_mcp_avg * 0.8)

    def _count_extended_fingers(self, lm: list[HandLandmark]) -> int:
        """
        统计伸展开的手指数量（拇指除外）
        通过比较指尖 y 坐标与 PIP/DIP 关节 y 坐标来判断
        """
        count = 0

        # 食指：指尖 y < PIP y（指尖在上方/更远）
        if lm[LandmarkIndex.INDEX_FINGER_TIP].y < lm[LandmarkIndex.INDEX_FINGER_PIP].y:
            count += 1

        # 中指
        if lm[LandmarkIndex.MIDDLE_FINGER_TIP].y < lm[LandmarkIndex.MIDDLE_FINGER_PIP].y:
            count += 1

        # 无名指
        if lm[LandmarkIndex.RING_FINGER_TIP].y < lm[LandmarkIndex.RING_FINGER_PIP].y:
            count += 1

        # 小指
        if lm[LandmarkIndex.PINKY_TIP].y < lm[LandmarkIndex.PINKY_PIP].y:
            count += 1

        return count

    def _detect_finger_count(self, lm: list[HandLandmark], current_time: float) -> str:
        """
        检测伸出 1 根或 2 根手指（拇指不算）
        需要稳定保持一定帧数后才触发，并有冷却时间防止连续触发
        """
        if current_time < self._finger_cooldown_until:
            return ""

        extended = self._count_extended_fingers(lm)
        stable_frames = max(5, int(30 * config.ADAPTIVE_STABILITY_SECONDS + 0.2))

        # 检测 1 指（食指）
        if extended == 1:
            self._finger_stable_frames["one_finger"] += 1
            self._finger_stable_frames["two_fingers"] = 0
            self._finger_triggered["two_fingers"] = False

            if self._finger_stable_frames["one_finger"] >= stable_frames and not self._finger_triggered["one_finger"]:
                self._finger_triggered["one_finger"] = True
                self._finger_cooldown_until = current_time + config.SWIPE_COOLDOWN_SECONDS
                return "one_finger"
        # 检测 2 指（食指 + 中指）
        elif extended == 2:
            self._finger_stable_frames["two_fingers"] += 1
            self._finger_stable_frames["one_finger"] = 0
            self._finger_triggered["one_finger"] = False

            if self._finger_stable_frames["two_fingers"] >= stable_frames and not self._finger_triggered["two_fingers"]:
                self._finger_triggered["two_fingers"] = True
                self._finger_cooldown_until = current_time + config.SWIPE_COOLDOWN_SECONDS
                return "two_fingers"
        else:
            self._finger_stable_frames["one_finger"] = max(0, self._finger_stable_frames["one_finger"] - 1)
            self._finger_stable_frames["two_fingers"] = max(0, self._finger_stable_frames["two_fingers"] - 1)
            self._finger_triggered["one_finger"] = False
            self._finger_triggered["two_fingers"] = False

        return ""

    def _detect_special_gestures(self, lm: list[HandLandmark], current_time: float) -> str:
        """
        检测三个特殊手势（互斥）：
        - fist: 握拳（手指全弯曲）
        - thumbs_up: 竖大拇指（拇指伸直，其余全弯曲）
        - five_fingers: 五指张开（拇指不检测弯曲，其余4指全展开）
        """
        # 计算各指伸展状态
        index_ext = lm[LandmarkIndex.INDEX_FINGER_TIP].y < lm[LandmarkIndex.INDEX_FINGER_PIP].y
        middle_ext = lm[LandmarkIndex.MIDDLE_FINGER_TIP].y < lm[LandmarkIndex.MIDDLE_FINGER_PIP].y
        ring_ext = lm[LandmarkIndex.RING_FINGER_TIP].y < lm[LandmarkIndex.RING_FINGER_PIP].y
        pinky_ext = lm[LandmarkIndex.PINKY_TIP].y < lm[LandmarkIndex.PINKY_PIP].y
        four_ext = sum([index_ext, middle_ext, ring_ext, pinky_ext])

        # 拇指伸展判断：拇指尖 x < 拇指IP x（对于右手），反之左手
        thumb_ext = lm[LandmarkIndex.THUMB_TIP].x < lm[LandmarkIndex.THUMB_IP].x

        # ---- 握拳：4根手指全弯曲，拇指可以随意 ---- 
        if four_ext == 0:
            self._fist_stable_count += 1
            self._thumbs_up_stable_count = 0
            self._five_fingers_stable_count = 0
            self._thumbs_up_triggered = False
            self._five_fingers_triggered = False

            if self._fist_stable_count >= config.FIST_STABLE_FRAMES and not self._fist_triggered:
                self._fist_triggered = True
                return "fist"
        else:
            self._fist_stable_count = 0
            self._fist_triggered = False

        # ---- 竖大拇指：拇指伸展，其余4指全弯曲 ----
        if thumb_ext and four_ext == 0:
            self._thumbs_up_stable_count += 1
            self._five_fingers_stable_count = 0
            self._five_fingers_triggered = False

            if self._thumbs_up_stable_count >= config.THUMBS_UP_STABLE_FRAMES and not self._thumbs_up_triggered:
                self._thumbs_up_triggered = True
                return "thumbs_up"
        else:
            self._thumbs_up_stable_count = 0
            self._thumbs_up_triggered = False

        # ---- 五指张开：4根手指全展开 ----
        if four_ext == 4:
            self._five_fingers_stable_count += 1
            if self._five_fingers_stable_count >= config.FIVE_FINGERS_STABLE_FRAMES and not self._five_fingers_triggered:
                self._five_fingers_triggered = True
                return "five_fingers"
        else:
            self._five_fingers_stable_count = 0
            self._five_fingers_triggered = False

        return ""

    def _detect_heart_gesture(self, lm: list[HandLandmark], current_time: float) -> str:
        """
        检测比心手势（拇指尖+食指尖交叉形成心形）
        特征：拇指与食指指尖距离极小（交叉/捏合），中指/无名指/小指伸直张开
        稳定触发后返回 "heart_gesture"（标记当前页为重点页）
        """
        if current_time < self._heart_cooldown_until:
            return ""

        thumb_tip = np.array([lm[LandmarkIndex.THUMB_TIP].x, lm[LandmarkIndex.THUMB_TIP].y])
        index_tip = np.array([lm[LandmarkIndex.INDEX_FINGER_TIP].x, lm[LandmarkIndex.INDEX_FINGER_TIP].y])
        distance = np.linalg.norm(thumb_tip - index_tip)

        # 拇指和食指必须很近（交叉/捏合），比 OK 手势更近
        if distance > config.OK_GESTURE_DISTANCE_THRESHOLD / 1500.0:
            self._heart_stable_count = 0
            return ""

        # 检查中指、无名指、小指是否伸展
        wrist = np.array([lm[LandmarkIndex.WRIST].x, lm[LandmarkIndex.WRIST].y])
        mcp_avg_x = (lm[LandmarkIndex.MIDDLE_FINGER_MCP].x + lm[LandmarkIndex.RING_FINGER_MCP].x + lm[LandmarkIndex.PINKY_MCP].x) / 3
        mcp_avg_y = (lm[LandmarkIndex.MIDDLE_FINGER_MCP].y + lm[LandmarkIndex.RING_FINGER_MCP].y + lm[LandmarkIndex.PINKY_MCP].y) / 3
        mcp_avg = np.array([mcp_avg_x, mcp_avg_y])
        dist_mcp_avg = np.linalg.norm(mcp_avg - wrist)

        middle_tip = np.array([lm[LandmarkIndex.MIDDLE_FINGER_TIP].x, lm[LandmarkIndex.MIDDLE_FINGER_TIP].y])
        ring_tip = np.array([lm[LandmarkIndex.RING_FINGER_TIP].x, lm[LandmarkIndex.RING_FINGER_TIP].y])
        pinky_tip = np.array([lm[LandmarkIndex.PINKY_TIP].x, lm[LandmarkIndex.PINKY_TIP].y])

        fingers_extended = (
            np.linalg.norm(middle_tip - wrist) > dist_mcp_avg * 0.8 and
            np.linalg.norm(ring_tip - wrist) > dist_mcp_avg * 0.8 and
            np.linalg.norm(pinky_tip - wrist) > dist_mcp_avg * 0.8
        )

        if not fingers_extended:
            self._heart_stable_count = 0
            return ""

        # 稳定帧数检测
        self._heart_stable_count += 1
        if self._heart_stable_count >= config.HEART_STABLE_FRAMES and not self._heart_triggered:
            self._heart_triggered = True
            self._heart_cooldown_until = current_time + 3.0  # 3秒冷却，避免连续标记
            self._special_cooldown_until = current_time + 3.0
            return "heart_gesture"

        return ""

    def _detect_three_fingers(self, lm: list[HandLandmark], current_time: float) -> str:
        """
        检测三指（食指+中指+无名指竖起，小指弯曲）
        稳定触发后返回 "three_fingers"（切换演讲稿显示/隐藏）
        """
        extended = self._count_extended_fingers(lm)

        # 三指 = 食指+中指+无名指伸展（扩展计数=3），且拇指随意，小指必须弯曲
        if extended == 3:
            self._three_fingers_stable_count += 1
            if self._three_fingers_stable_count >= config.THREE_FINGERS_STABLE_FRAMES and not self._three_fingers_triggered:
                self._three_fingers_triggered = True
                self._special_cooldown_until = current_time + 2.0  # 2秒冷却，避免连续触发
                return "three_fingers"
        else:
            self._three_fingers_stable_count = 0
            self._three_fingers_triggered = False

        return ""

    def _detect_swipe(self, lm: list[HandLandmark]) -> str:
        """
        检测手掌滑动（左滑/右滑）
        使用掌心（中指 MCP）的 x 坐标变化
        """
        palm_x = lm[LandmarkIndex.MIDDLE_FINGER_MCP].x

        if self._prev_palm_x is None:
            self._prev_palm_x = palm_x
            self._palm_x_history.clear()
            self._palm_x_history.append(palm_x)
            return ""

        self._palm_x_history.append(palm_x)

        # 计算滑动位移（用历史均值减少抖动）
        if len(self._palm_x_history) >= 3:
            avg_x = np.mean(self._palm_x_history)
            dx = avg_x - self._prev_palm_x

            # 转换为像素位移（假设画面宽度 640）
            threshold = config.SWIPE_THRESHOLD / 640.0

            if dx > threshold:
                self._prev_palm_x = avg_x
                self._palm_x_history.clear()
                return "swipe_right"
            elif dx < -threshold:
                self._prev_palm_x = avg_x
                self._palm_x_history.clear()
                return "swipe_left"

        self._prev_palm_x = palm_x
        return ""

    def get_last_gesture(self) -> str:
        return self._last_gesture

    def reset(self):
        """重置状态（模式切换时调用）"""
        self._ok_stable_count = 0
        self._ok_triggered = False
        self._swipe_cooldown_until = 0.0
        self._finger_stable_frames["one_finger"] = 0
        self._finger_stable_frames["two_fingers"] = 0
        self._finger_triggered["one_finger"] = False
        self._finger_triggered["two_fingers"] = False
        self._finger_cooldown_until = 0.0
        self._fist_stable_count = 0
        self._fist_triggered = False
        self._thumbs_up_stable_count = 0
        self._thumbs_up_triggered = False
        self._five_fingers_stable_count = 0
        self._five_fingers_triggered = False
        self._special_cooldown_until = 0.0
        self._heart_stable_count = 0
        self._heart_triggered = False
        self._heart_cooldown_until = 0.0
        self._three_fingers_stable_count = 0
        self._three_fingers_triggered = False
        self._last_hand_count = 0
        self._last_gesture = "none"