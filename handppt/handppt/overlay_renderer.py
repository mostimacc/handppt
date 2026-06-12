"""
画面叠加渲染模块
在摄像头画面顶部叠加：模式状态、手势/语音信息、PPT页码、高亮文字等
使用 Pillow (PIL) 渲染中文字符，解决 OpenCV 无法显示中文/emoji 的问题
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config


class OverlayRenderer:
    """画面叠加渲染器（支持中文和 emoji）"""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        # 当前模式
        self._current_mode = "gesture"
        # 手势识别结果
        self._gesture_text = ""
        # 语音识别文本
        self._voice_text = ""
        # PPT 页码
        self._page_info = ""

        # 加载中文字体（尝试多个路径）
        self._font = self._load_font()

    def _load_font(self, size: int = 20) -> ImageFont.FreeTypeFont:
        """加载支持中文的字体"""
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",          # 微软雅黑
            "C:/Windows/Fonts/msyhbd.ttc",        # 微软雅黑粗体
            "C:/Windows/Fonts/simsun.ttc",         # 宋体
            "C:/Windows/Fonts/simhei.ttf",         # 黑体
            "C:/Windows/Fonts/yahei.ttf",          # 微软雅黑（备选）
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttf",  # Linux 文泉驿
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto
        ]
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, size, encoding="unic")
                # 测试是否能渲染中文
                test_draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
                test_draw.text((0, 0), "测试", font=font)
                return font
            except Exception:
                continue
        # 如果所有字体都找不到，使用默认字体（可能不支持中文）
        print("[渲染] 未找到中文字体，中文可能显示为方框")
        return ImageFont.load_default()

    def get_font(self, size: int = 20) -> ImageFont.FreeTypeFont:
        """获取指定大小的字体"""
        if self._font.__class__.__name__ == "FreeTypeFont":
            try:
                return self._font.font_variant(size=size)
            except Exception:
                pass
        # 重新加载不同大小的字体
        return self._load_font(size)

    def set_mode(self, mode: str):
        self._current_mode = mode

    def set_gesture(self, text: str):
        self._gesture_text = text

    def set_voice_text(self, text: str):
        self._voice_text = text

    def set_page_info(self, info: str):
        self._page_info = info

    def get_page_info(self) -> str:
        return self._page_info


    def _draw_text(self, draw: ImageDraw, text: str, pos: tuple,
                   font_size: int, color: tuple, anchor: str = "lt"):
        """
        在 PIL ImageDraw 上绘制文本
        color: (R, G, B) 0-255
        anchor: "lt" 左上, "mt" 中上, "rt" 右上
        """
        font = self.get_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x, y = pos
        if anchor == "mm":  # 完全居中
            x = x - text_w // 2
            y = y - text_h // 2
        elif "m" in anchor:  # 水平居中
            x = x - text_w // 2
        elif "r" in anchor:  # 右对齐
            x = x - text_w

        draw.text((x, y), text, font=font, fill=color)

    def render(self, frame: np.ndarray) -> np.ndarray:
        """在帧上叠加所有 UI 元素（使用 PIL 渲染中文）"""

        # 转换为 PIL Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil_img)

        # ---- 顶部状态栏 ----
        mode_str = "🎯 手势控制" if self._current_mode == "gesture" else "🎤 语音识别"
        mode_color = (0, 255, 0) if self._current_mode == "gesture" else (255, 255, 0)

        # 模式名称（左上角）
        self._draw_text(draw, mode_str, (10, 10), font_size=22, color=mode_color)

        # 页码信息（右上角）
        if self._page_info:
            self._draw_text(draw, self._page_info, (self.width - 10, 10),
                           font_size=18, color=(0, 255, 0), anchor="rt")

        # ---- 左侧：手势 / 语音信息 ----
        info_y = 40

        if self._current_mode == "gesture":
            if self._gesture_text:
                self._draw_text(draw, f"手势: {self._gesture_text}", (10, info_y),
                               font_size=16, color=(0, 255, 0))
            # 底部提示
            tip_y = self.height - 30
            self._draw_text(draw, "🤏 OK手势 → 语音模式", (10, tip_y),
                           font_size=14, color=(200, 200, 200))
        else:
            if self._voice_text:
                self._draw_text(draw, f"语音: {self._voice_text}", (10, info_y),
                               font_size=16, color=(255, 200, 0))
            # 底部提示
            tip_y = self.height - 30
            self._draw_text(draw, "说 \"ok\" → 手势模式", (10, tip_y),
                           font_size=14, color=(200, 200, 200))

        # 转回 OpenCV BGR
        if pil_img.mode == "RGBA":
            pil_img = pil_img.convert("RGB")
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return frame