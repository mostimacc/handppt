# ============================================
# 手势翻页笔 + 语音识别PPT控制 - 配置文件
# ============================================

# ---------- 摄像头设置 ----------
CAMERA_ID = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ---------- MediaPipe 设置 ----------
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5
MAX_NUM_HANDS = 1

# ---------- 手势-按键映射表 ----------
GESTURE_KEY_MAP = {
    "fist": {                    # 握拳
        "key": "space",
        "description": "播放/暂停"
    },
    "open_palm": {               # 手掌张开
        "key": "esc",
        "description": "退出/返回"
    },
    "index_point_up": {          # 食指指天
        "key": "up",
        "description": "向上/音量+"
    },
    "victory": {                 # 胜利手势 食指+中指
        "key": "down",
        "description": "向下/音量-"
    },
    "index_point_left": {        # 食指指左
        "key": "left",
        "description": "向左/上一页"
    },
    "index_point_right": {       # 食指指右
        "key": "right",
        "description": "向右/下一页"
    },
    "thumbs_up": {               # 竖大拇指
        "key": "enter",
        "description": "确认/回车"
    },
}

# ---------- PPT 手势翻页 ----------
SWIPE_THRESHOLD = 80            # 滑动触发阈值（像素），手掌横移超过此值触发翻页
SWIPE_COOLDOWN_SECONDS = 2.0    # 翻页冷却时间（秒），防止连续触发
PPT_NEXT_KEY = "pagedown"       # 下一页按键
PPT_PREV_KEY = "pageup"         # 上一页按键
DEFAULT_PPT_PATH = "C:/Users/cc/Desktop/手势识别控制PPT汇报 (3).pptx"  # 默认 PPT 文件路径

# ---------- 自适应稳定与冷却 ----------
# 稳定性目标时长（秒）：稳定帧数 = max(3, FPS × 此值)
# 即不管帧率高低，始终保证约 0.2 秒的确认时间
ADAPTIVE_STABILITY_SECONDS = 0.2
# 冷却帧数比：冷却时间 = max(0.3, min(1.5, 此值 / FPS))
# 即约等于 N 帧的间隔，自动适应帧率变化
ADAPTIVE_COOLDOWN_FRAMES = 6

# ---------- 显示设置 ----------
SHOW_HELP = True               # 是否在画面上显示帮助信息
FONT_SCALE = 0.6               # 文字缩放比例
FONT_COLOR = (0, 255, 0)       # 普通文字颜色（绿色 BGR 格式）
HIGHLIGHT_COLOR = (0, 255, 255)  # 高亮文字颜色（黄色 BGR 格式）

# ============================================
# 新增：模式切换 & 语音识别设置
# ============================================

# ---------- 模式切换设置 ----------
# 初始模式："gesture" 或 "voice"
INITIAL_MODE = "gesture"
# OK 手势判定阈值（拇指尖与食指尖的像素距离）
OK_GESTURE_DISTANCE_THRESHOLD = 40
# 从语音切回手势的唤醒词（小写，去掉标点）
WAKE_WORD = "ok"

# ---------- 语音识别设置 ----------
# Vosk 中文模型路径（下载后存放的目录名）
VOSK_MODEL_DIR = "vosk-model-cn-0.22"
# 采样率
SAMPLE_RATE = 16000
# 静默超时时间（秒），超过此时间无有效语音则重置识别
SILENCE_TIMEOUT = 2.0

# ---------- 额外手势稳定帧数要求 ----------
FIST_STABLE_FRAMES = 8          # 握拳稳定帧数
THUMBS_UP_STABLE_FRAMES = 8     # 竖大拇指稳定帧数
FIVE_FINGERS_STABLE_FRAMES = 6  # 五张稳定帧数
HEART_STABLE_FRAMES = 10        # 比心跳稳定帧数
THREE_FINGERS_STABLE_FRAMES = 8 # 三指(食指+中指+无名指)稳定帧数

# ---------- PPT 文字匹配设置 ----------
# 匹配相似度阈值，用于判定语音是否与幻灯片文字匹配（0.0 ~ 1.0）
TEXT_MATCH_THRESHOLD = 0.8
# 高亮文字的显示时长（帧数）
HIGHLIGHT_DURATION_FRAMES = 60

# ---------- DeepSeek 演讲稿生成 ----------
# DeepSeek API Key（可在设置面板中填写，或在此预设）
DEEPSEEK_API_KEY = ""
# DeepSeek 模型名称
DEEPSEEK_MODEL = "deepseek-chat"
# 单页演讲稿最大 token 数
DEEPSEEK_MAX_TOKENS = 500
# 创意度（0.0 = 严谨，1.0 = 创意）
DEEPSEEK_TEMPERATURE = 0.7
# 是否在翻页时自动显示底部演讲稿提词器
SHOW_SPEECH_PROMPTER = True

# ---------- 演讲稿自动滚动（提词器）----------
# 是否启用自动滚动（True=自动滚动，False=只显示静态文字）
SPEECH_ENABLE_SCROLL = True
# 自动滚动间隔（毫秒），每多少毫秒滚动一行
SPEECH_SCROLL_INTERVAL_MS = 3000
# 自动滚动速度（每次滚动的像素行数，1=逐行滚动）
SPEECH_SCROLL_STEP = 1
# 用户手动操作后暂停滚动的恢复时间（秒）
SPEECH_SCROLL_PAUSE_SECONDS = 3
