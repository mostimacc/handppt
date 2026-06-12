"""
屏幕叠加层模块
在 Windows 桌面创建一个透明的、置顶的、点击穿透的覆盖层。

演讲稿以单行跑马灯形式显示 → 从右向左水平滚动（类似新闻滚动字幕）

支持两种显示：
1. 演讲提示（跑马灯模式）- 代替完整的提词器
2. 实时语音字幕（居中小区域）
3. 翻页时淡入动画
"""

import math
import threading
import time
import tkinter as tk
import win32gui
import win32con

import config


class ScreenOverlay:
    """
    屏幕底部单行跑马灯 + 字幕叠加层
    通过队列线程安全地接受主程序发来的显示/隐藏命令
    """

    def __init__(self):
        self._root = None
        self._subtitle_label = None    # 白色语音字幕文字
        self._subtitle_frame = None    # 黑色背景条（字幕区域，30px高）

        # 演讲稿显示开关（默认显示）
        self._speech_visible = True

        # 跑马灯（单行横向滚动）
        self._marquee_label = None
        self._marquee_frame = None
        self._marquee_text = ""        # 完整演讲稿文本
        self._marquee_display = ""     # 当前窗口内显示的文字片段
        self._marquee_offset = 0       # 当前滚动偏移（字符位置，支持小数以实现平滑滚动）
        self._marquee_px_per_char = 0  # 每个字符的平均像素宽度
        self._marquee_max_chars = 0    # 可见区域能容纳的最大字符数
        self._marquee_total_width = 0  # 完整文本的总像素宽度

        self._speech_text = ""         # 当前演讲稿缓存
        self._last_speech_text = ""    # 上一段演讲稿（用于检测内容变化）
        self._speech_alpha = 0.0       # 淡入动画进度 (0.0~1.0)
        self._fade_timer_id = None     # 淡入动画定时器 ID
        self._running = False
        self._thread = None

        # 滚动定时器
        self._scroll_timer_id = None

        # 线程安全命令队列
        self._cmd_lock = threading.Lock()
        self._cmd_queue: list[tuple] = []

    # ==================== 公开接口（可在任何线程调用）====================

    def start(self):
        """在后台线程中启动叠加窗口"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        time.sleep(0.3)

    def show_subtitle(self, text: str):
        """白色实时语音字幕（黑色背景条内居中显示）"""
        with self._cmd_lock:
            self._cmd_queue.append(("show_subtitle", text))

    def show_speech(self, text: str):
        """
        演讲稿跑马灯提示 → 底部单行自右向左水平滚动
        翻页时显示当前页的演讲稿内容
        """
        with self._cmd_lock:
            self._cmd_queue.append(("show_speech", text))

    def toggle_speech_visibility(self):
        """切换演讲稿跑马灯的显示/隐藏"""
        with self._cmd_lock:
            self._cmd_queue.append(("toggle_speech", None))

    def clear_subtitle(self):
        """清除字幕并隐藏窗口"""
        with self._cmd_lock:
            self._cmd_queue.append(("clear_subtitle", None))

    def stop(self):
        """停止叠加窗口"""
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.quit)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2)

    # ==================== 内部实现 ====================

    def _run_tk(self):
        """在后台线程中创建并运行 tkinter 窗口"""
        self._root = tk.Tk()
        self._root.title("PPT字幕与演讲稿")

        # ----- 窗口样式 -----
        self._root.overrideredirect(True)          # 无标题栏 / 边框
        self._root.attributes('-topmost', True)     # 永远置顶
        self._root.configure(bg='#010101')          # 背景色（作为透明色）

        # 设置透明色（#010101 区域完全透明）
        self._root.wm_attributes('-transparentcolor', '#010101')

        # ----- 窗口尺寸 & 位置 -----
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        bar_height = 55    # 总窗口高：演讲跑马灯(35px) + 字幕条(20px)
        win_x = 0
        win_y = screen_height - bar_height - 15   # 距底部 15px

        self._root.geometry(f"{screen_width}x{bar_height}+{win_x}+{win_y}")

        # ===== 演讲稿跑马灯区域（单行，占大部分宽度）=====
        self._marquee_frame = tk.Frame(
            self._root,
            bg='#1a1a2e',              # 深蓝色背景
        )
        self._marquee_frame.place(x=0, y=0, relwidth=1, height=35)

        # 单行跑马灯 Label（初始隐藏）
        self._marquee_label = tk.Label(
            self._marquee_frame,
            text="",
            font=("Microsoft YaHei", 18),
            fg="#FFFFFF",
            bg='#1a1a2e',
            anchor="w",                 # 左对齐，模拟从右向左滚动
            padx=5,
        )
        self._marquee_label.place(x=0, y=0, relwidth=1, relheight=1)

        # ===== 语音字幕区域（最底部一行）=====
        subtitle_frame_y = 35
        subtitle_frame_h = 20

        self._subtitle_frame = tk.Frame(
            self._root,
            bg='#000000',
        )
        self._subtitle_frame.place(
            x=0, y=subtitle_frame_y, relwidth=1, height=subtitle_frame_h
        )

        self._subtitle_label = tk.Label(
            self._subtitle_frame,
            text="",
            font=("Microsoft YaHei", 12),
            fg="#AAAAAA",
            bg='#000000',
            anchor="center",
        )
        self._subtitle_label.place(relx=0.5, rely=0.5, anchor="center")

        # ----- 设置为点击穿透 -----
        self._set_click_through()

        # ----- 默认隐藏 -----
        self._root.withdraw()

        # ----- 启动定时轮询命令队列 -----
        self._poll_commands()
        self._root.mainloop()

    def _set_click_through(self):
        """设置窗口为点击穿透 (WS_EX_TRANSPARENT | WS_EX_LAYERED)"""
        try:
            hwnd = win32gui.GetParent(self._root.winfo_id())
            if hwnd:
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                new_style = (
                    ex_style |
                    win32con.WS_EX_LAYERED |
                    win32con.WS_EX_TRANSPARENT |
                    win32con.WS_EX_TOPMOST
                )
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def _get_text_width_pixels(self, text: str, font_size: int) -> int:
        """估算文本宽度（像素），用于跑马灯滚动计算"""
        # 中文字符约 1.2 * font_size，英文字符约 0.6 * font_size
        width = 0
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef':
                width += math.ceil(font_size * 1.2)     # 中文字符
            else:
                width += math.ceil(font_size * 0.65)    # 英文字符
        return width + 10  # 额外边距

    def _poll_commands(self):
        """定时轮询命令队列（在 tkinter 主线程中执行）"""
        if not self._running or not self._root:
            return

        while True:
            with self._cmd_lock:
                if not self._cmd_queue:
                    break
                item = self._cmd_queue.pop(0)

            cmd = item[0]
            try:
                if cmd == "show_subtitle" and len(item) >= 2 and item[1]:
                    text = item[1]
                    self._subtitle_label.config(text=text)
                    self._deiconify_if_needed()
                    self._root.lift()

                elif cmd == "show_speech" and len(item) >= 2 and item[1]:
                    text = item[1]
                    # 内容变化时才触发
                    if text != self._last_speech_text:
                        self._last_speech_text = text
                        self._speech_text = text

                        # 计算跑马灯参数
                        self._marquee_text = text
                        self._marquee_offset = 0   # 从头开始

                        # 获取可见区域宽度
                        self._root.update_idletasks()
                        if self._marquee_frame:
                            frame_width = self._marquee_frame.winfo_width()
                            if frame_width < 10:
                                frame_width = 600  # 保底值
                        else:
                            frame_width = 600

                        # 估算字符宽度和文本总宽
                        px_per_char = self._get_text_width_pixels("测", 18)
                        self._marquee_px_per_char = px_per_char
                        self._marquee_max_chars = max(1, frame_width // px_per_char)
                        self._marquee_total_width = self._get_text_width_pixels(text, 18)

                        # 更新显示
                        if self._marquee_label:
                            self._marquee_label.config(
                                text=text[:self._marquee_max_chars]
                            )

                        # 显示框架
                        if self._marquee_frame:
                            try:
                                self._marquee_frame.lift()
                            except Exception:
                                pass

                        self._deiconify_if_needed()
                        self._root.lift()

                        # 启动淡入动画
                        self._speech_alpha = 0.0
                        self._start_fade_in()

                        # 如果文本长度超过可见区域，启动跑马灯滚动
                        self._stop_marquee()
                        if self._marquee_total_width > frame_width:
                            self._start_marquee()
                        else:
                            # 文本较短，居中显示即可
                            if self._marquee_label:
                                self._marquee_label.config(anchor="center")

                elif cmd == "toggle_speech":
                    self._speech_visible = not self._speech_visible
                    if self._speech_visible:
                        # 恢复显示：如果有演讲稿内容就显示
                        if self._speech_text:
                            self._deiconify_if_needed()
                            self._root.lift()
                            if self._marquee_frame:
                                try:
                                    self._marquee_frame.lift()
                                except Exception:
                                    pass
                            # 重新启动跑马灯
                            self._stop_marquee()
                            if self._marquee_total_width > self._marquee_frame.winfo_width():
                                self._start_marquee()
                    else:
                        # 隐藏演讲稿区域
                        self._stop_marquee()
                        if self._marquee_frame:
                            try:
                                self._marquee_frame.lower()
                            except Exception:
                                pass
                        if self._marquee_label:
                            self._marquee_label.config(text="")

                elif cmd == "clear_subtitle":
                    self._subtitle_label.config(text="")
                    self._speech_text = ""
                    self._last_speech_text = ""
                    self._speech_alpha = 0.0
                    self._stop_marquee()
                    if self._fade_timer_id:
                        try:
                            self._root.after_cancel(self._fade_timer_id)
                        except Exception:
                            pass
                        self._fade_timer_id = None
                    if self._marquee_label:
                        self._marquee_label.config(text="")
                        self._marquee_label.config(anchor="w")
                    try:
                        self._root.withdraw()
                    except Exception:
                        pass
            except Exception:
                import traceback
                traceback.print_exc()

        self._root.after(50, self._poll_commands)

    # ==================== 跑马灯滚动（水平）====================

    def _start_marquee(self):
        """启动跑马灯: 从右向左水平滚动"""
        self._scroll_timer_id = self._root.after(
            config.SPEECH_SCROLL_INTERVAL_MS, self._tick_marquee
        )

    def _stop_marquee(self):
        """停止跑马灯"""
        if self._scroll_timer_id:
            try:
                self._root.after_cancel(self._scroll_timer_id)
            except Exception:
                pass
            self._scroll_timer_id = None

    def _tick_marquee(self):
        """跑马灯每秒滚一帧：向右偏移一个字符，当文本尾部离开左边缘后复位"""
        if not self._marquee_label or not self._speech_text:
            return

        text = self._speech_text
        text_len = len(text)

        if text_len <= self._marquee_max_chars:
            return  # 不需要滚动

        # 每次偏移 +1 个字符位置
        self._marquee_offset += 1

        # 当偏移量超过文本长度时，复位（无限循环）
        if self._marquee_offset >= text_len:
            self._marquee_offset = 0

        # 计算当前可见的文本片段
        # 为了从右向左的效果，从 offset 开始取 max_chars 个字符显示
        start = self._marquee_offset
        end = start + self._marquee_max_chars

        if end <= text_len:
            visible = text[start:end]
        else:
            # 接近末尾时，显示剩余部分 + 空白 + 开头部分（无缝循环效果）
            remaining = text[start:]
            wrap_needed = end - text_len
            visible = remaining + "   " + text[:wrap_needed]

        self._marquee_label.config(text=visible, anchor="w")

        # 继续循环
        self._scroll_timer_id = self._root.after(
            config.SPEECH_SCROLL_INTERVAL_MS, self._tick_marquee
        )

    # ==================== 淡入动画 ====================

    def _start_fade_in(self):
        """启动淡入动画：每 50ms 增加 alpha，0.5 秒内完成"""
        if not self._root:
            return

        self._speech_alpha = min(1.0, self._speech_alpha + 0.1)
        alpha = self._speech_alpha
        if self._marquee_label:
            # 文字颜色从淡灰色逐渐变为白色
            r = int(200 + (255 - 200) * alpha)
            g = int(200 + (255 - 200) * alpha)
            b = int(200 + (255 - 200) * alpha)
            self._marquee_label.config(fg=f'#{r:02x}{g:02x}{b:02x}')
        if self._marquee_frame:
            # 背景色从深色逐渐变为目标色
            r = int(10 + (26 - 10) * alpha)
            g = int(10 + (26 - 10) * alpha)
            b = int(46 + (46 - 46) * alpha)
            self._marquee_frame.config(bg=f'#{r:02x}{g:02x}{b:02x}')
            self._marquee_label.config(bg=f'#{r:02x}{g:02x}{b:02x}')

        if self._speech_alpha < 1.0:
            self._fade_timer_id = self._root.after(50, self._start_fade_in)
        else:
            self._fade_timer_id = None

    def _deiconify_if_needed(self):
        """如果窗口当前隐藏则显示"""
        try:
            state = self._root.state()
            if state == "withdrawn" or state == "iconic":
                self._root.deiconify()
        except Exception:
            pass