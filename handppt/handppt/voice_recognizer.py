"""
语音识别模块
封装 Vosk 离线语音识别引擎，提供：
1. 持续监听麦克风输入（仅在被激活时启动）
2. 实时语音转文字
3. 静默检测与超时重置
"""

import json
import queue
import re
import threading
import time
from pathlib import Path

import config


class VoiceRecognizer:
    """语音识别器（基于 Vosk 离线引擎）"""

    def __init__(self):
        self._model = None
        self._recognizer = None
        self._audio_interface = None
        self._audio_stream = None
        self._listening = False
        self._thread = None
        self._result_queue = queue.Queue()
        self._initialized = False

        # 识别结果
        self._partial_text = ""  # 部分识别结果
        self._final_text = ""    # 最终识别结果
        self._last_activity_time = time.time()
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """初始化 Vosk 模型和音频接口"""
        try:
            from vosk import Model, KaldiRecognizer
        except ImportError:
            print("[Voice] vosk 未安装")
            return False

        try:
            import pyaudio
        except ImportError:
            print("[Voice] pyaudio 未安装")
            return False

        # 查找 Vosk 模型
        model_path = self._find_model_path()
        if not model_path:
            print(f"[Voice] 未找到 Vosk 中文模型。请下载后放入以下目录之一：")
            print(f"       1. {config.VOSK_MODEL_DIR} （当前目录）")
            print(f"       2. {Path.cwd() / 'model'}")
            print(f"       下载地址: https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip")
            return False

        try:
            print(f"[Voice] 正在加载 Vosk 模型: {model_path} ...")
            self._model = Model(str(model_path))
            self._recognizer = KaldiRecognizer(self._model, config.SAMPLE_RATE)
            self._recognizer.SetWords(True)

            # 初始化 PyAudio
            self._audio_interface = pyaudio.PyAudio()
            self._audio_stream = self._audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=config.SAMPLE_RATE,
                input=True,
                frames_per_buffer=4000,
            )

            self._initialized = True
            print("[Voice] 语音识别引擎初始化成功")
            return True

        except Exception as e:
            print(f"[Voice] 初始化失败: {e}")
            return False

    def _find_model_path(self) -> str | None:
        """查找 Vosk 模型路径（支持嵌套目录）"""
        candidates = [
            config.VOSK_MODEL_DIR,
            str(Path.cwd() / config.VOSK_MODEL_DIR),
            str(Path(__file__).parent / config.VOSK_MODEL_DIR),
            "vosk-model-small-cn-0.22",
            "model",
        ]
        for cand in candidates:
            path = Path(cand)
            if path.exists() and path.is_dir():
                # 检查目录下是否有模型文件（am 目录）
                am_file = path / "am"
                if am_file.exists():
                    return str(path)
                # 递归搜索子目录（处理嵌套解压的情况）
                for subdir in path.rglob("am"):
                    if subdir.is_dir():
                        return str(subdir.parent)
        return None

    def start_listening(self):
        """
        启动语音识别监听（按需调用，不监听时音频线程不运行）
        与旧的 start() 不同，此方法只在需要时才真正打开音频流
        """
        if not self._initialized:
            print("[Voice] 引擎未初始化，无法启动监听")
            return

        if self._listening:
            return

        # 重置识别器状态
        try:
            from vosk import KaldiRecognizer
            self._recognizer = KaldiRecognizer(self._model, config.SAMPLE_RATE)
            self._recognizer.SetWords(True)
        except Exception:
            pass

        # 清空队列
        while not self._result_queue.empty():
            try:
                self._result_queue.get_nowait()
            except queue.Empty:
                break

        with self._lock:
            self._partial_text = ""
            self._final_text = ""
            self._last_activity_time = time.time()

        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[Voice] 语音识别监听已启动")

    def stop_listening(self):
        """停止语音识别监听"""
        self._listening = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # 清空队列
        while not self._result_queue.empty():
            try:
                self._result_queue.get_nowait()
            except queue.Empty:
                break

        with self._lock:
            self._partial_text = ""
            self._final_text = ""

        print("[Voice] 语音识别监听已停止")

    def _listen_loop(self):
        """音频监听循环（在独立线程中运行）"""
        while self._listening and self._audio_stream:
            try:
                data = self._audio_stream.read(4000, exception_on_overflow=False)
                if len(data) == 0:
                    continue

                if self._recognizer.AcceptWaveform(data):
                    # 获得最终识别结果
                    result = json.loads(self._recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        with self._lock:
                            self._final_text = text
                            self._partial_text = ""
                            self._last_activity_time = time.time()
                        self._result_queue.put(("final", text))
                else:
                    # 部分识别结果
                    partial = json.loads(self._recognizer.PartialResult())
                    partial_text = partial.get("partial", "").strip()
                    if partial_text:
                        with self._lock:
                            self._partial_text = partial_text
                            self._last_activity_time = time.time()
                        self._result_queue.put(("partial", partial_text))

                # 静默超时检测
                with self._lock:
                    if time.time() - self._last_activity_time > config.SILENCE_TIMEOUT and self._final_text:
                        self._final_text = ""
                        self._partial_text = ""

            except Exception as e:
                if self._listening:
                    print(f"[Voice] 监听异常: {e}")
                    time.sleep(0.1)

    def is_listening(self) -> bool:
        """是否正在监听"""
        return self._listening

    def get_result(self) -> tuple[str, str] | None:
        """获取识别结果（非阻塞），返回 (type, text)"""
        try:
            return self._result_queue.get_nowait()
        except queue.Empty:
            return None

    def get_partial_text(self) -> str:
        """获取当前部分识别文本"""
        with self._lock:
            return self._partial_text

    def get_final_text(self) -> str:
        """获取当前最终识别文本"""
        with self._lock:
            return self._final_text

    def consume_final_text(self) -> str:
        """获取并清空最终识别文本"""
        with self._lock:
            text = self._final_text
            self._final_text = ""
            return text

    # 保留旧接口兼容
    def start(self):
        self.start_listening()

    def stop(self):
        self.stop_listening()

    def close(self):
        """释放资源"""
        self.stop_listening()
        if self._audio_stream:
            self._audio_stream.close()
            self._audio_stream = None
        if self._audio_interface:
            self._audio_interface.terminate()
            self._audio_interface = None
        self._model = None
        self._recognizer = None
        self._initialized = False