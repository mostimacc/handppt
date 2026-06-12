"""
手部检测模块
封装 MediaPipe Hand Landmarker（Task API，需要 hand_landmarker.task 模型文件）
"""

import os

import cv2
import numpy as np

# MediaPipe 导入
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    _HAS_MEDIAPIPE = True
except ImportError:
    _HAS_MEDIAPIPE = False

import config


class HandLandmark:
    """单个手部关键点"""
    def __init__(self, x: float, y: float, z: float):
        self.x = x  # 归一化坐标 0~1
        self.y = y
        self.z = z


class HandData:
    """单只手的所有数据"""
    def __init__(self, landmarks: list, handedness: str = ""):
        self.landmarks = [HandLandmark(lm.x, lm.y, lm.z) for lm in landmarks]
        self.handedness = handedness  # "Left" or "Right"


class DetectionResult:
    """检测结果"""
    def __init__(self, hands: list[HandData]):
        self.hands = hands

    @property
    def num_hands(self) -> int:
        return len(self.hands)

    def get_hand(self, index: int = 0) -> HandData | None:
        if 0 <= index < len(self.hands):
            return self.hands[index]
        return None


class HandDetector:
    """手部检测器：封装 MediaPipe Hand Landmarker"""

    def __init__(self):
        # 模型文件与脚本在同一目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self._model_asset_path = os.path.join(script_dir, "hand_landmarker.task")
        self._detector = None
        self._initialized = False

    def initialize(self) -> bool:
        """初始化 MediaPipe 手部检测器"""
        if not _HAS_MEDIAPIPE:
            print("[Hand] mediapipe 未安装")
            return False

        try:
            base_options = python.BaseOptions(model_asset_path=self._model_asset_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=config.MAX_NUM_HANDS,
                min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_hand_presence_confidence=config.MIN_TRACKING_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self._detector = vision.HandLandmarker.create_from_options(options)
            self._initialized = True
            print("[Hand] MediaPipe 手部检测器初始化成功")
            return True
        except Exception as e:
            print(f"[Hand] 初始化失败: {e}")
            return False

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """检测一帧图像中的手部，返回检测结果"""
        if not self._initialized or self._detector is None:
            return DetectionResult([])

        try:
            # 转换为 MediaPipe Image
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # 检测
            result = self._detector.detect(mp_image)

            hands = []
            if result.hand_landmarks:
                for i, landmarks in enumerate(result.hand_landmarks):
                    handedness = ""
                    if hasattr(result, 'handedness') and len(result.handedness) > i:
                        handedness = result.handedness[i][0].category_name
                    hands.append(HandData(landmarks, handedness))

            return DetectionResult(hands)

        except Exception as e:
            # print(f"[Hand] 检测异常: {e}")
            return DetectionResult([])

    def close(self):
        """释放资源"""
        if self._detector is not None:
            self._detector.close()
            self._detector = None
        self._initialized = False