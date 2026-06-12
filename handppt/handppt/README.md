# 手语/语音 PPT 控制器

基于 **MediaPipe 手部检测** + **Vosk 离线语音识别** + **DeepSeek AI 演讲稿生成**，通过手势、语音或键盘控制 PPT 翻页，支持 AI 自动生成演讲稿并滚动显示。

## 快速开始

```bash
pip install -r requirements.txt
```

1. 下载 [hand_landmarker.task](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task)，放入 `handppt/` 目录
2. 下载 [vosk-model-cn-0.22.zip](https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip)，解压后放到项目根目录（确保目录中包含 `am` 文件夹）
3. 运行 `python main.py`

> AI 演讲稿生成需 [DeepSeek API Key](https://platform.deepseek.com/)（可选）

## 使用流程

选择 PPTX → 设置面板（填 API Key + 生成/编辑演讲稿） → 开始演示 → 手势控制 + 底部提词器

## 手势一览

| 手势 | 动作 | 功能 |
|------|------|------|
| 手掌 右滑 | 五指张开向右滑动 | 下一页 |
| 手掌 左滑 | 五指张开向左滑动 | 上一页 |
| 食指指天 | 仅食指伸直 | 下一页 |
| V 手势 | 食+中指伸直 | 上一页 |
| OK 手势 | 拇+食捏合，其余张开 | ⇄ 语音模式 |
| 竖拇指 | 拇指伸直，四指弯曲 | 跳首页 |
| 五指张开 | 全部伸直张开 | 跳末页 |
| 比心 | 拇+食交叉，其余张开 | 标为重点页 |
| 三指 | 食+中+无名指竖起 | 切换提词器 |

## 语音命令

说"下一页/上一张/黑屏/结束放映/首页/末页"等控制，说"ok"切回手势模式。也可直接念 PPT 文字触发字幕匹配。

## 键盘快捷键

| 键 | 功能 |
|----|------|
| ESC | 退出 |
| G | 手势模式 |
| V | 语音模式 |
| N/P | 下一/上一页 |
| R | 重点页报告 |

## 配置文件 (`config.py`)

### 摄像头

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_ID` | 0 | 摄像头编号 |
| `CAMERA_WIDTH` | 640 | 画面宽 |
| `CAMERA_HEIGHT` | 480 | 画面高 |

### 手势识别

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SWIPE_THRESHOLD` | 80 | 滑动触发阈值(px) |
| `SWIPE_COOLDOWN_SECONDS` | 2.0 | 翻页冷却(s) |
| `ADAPTIVE_STABILITY_SECONDS` | 0.2 | 稳定时长(s) |
| `OK_GESTURE_DISTANCE_THRESHOLD` | 40 | OK 判定距离 |
| `FIST_STABLE_FRAMES` | 8 | 握拳稳定帧数 |
| `THUMBS_UP_STABLE_FRAMES` | 8 | 竖拇指稳定帧数 |
| `FIVE_FINGERS_STABLE_FRAMES` | 6 | 五指稳定帧数 |
| `HEART_STABLE_FRAMES` | 10 | 比心稳定帧数 |
| `THREE_FINGERS_STABLE_FRAMES` | 8 | 三指稳定帧数 |

### 语音识别

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `VOSK_MODEL_DIR` | vosk-model-cn-0.22 | 模型目录（自动搜索含 `am` 的子目录） |
| `SAMPLE_RATE` | 16000 | 采样率 |
| `SILENCE_TIMEOUT` | 2.0 | 静默超时(s) |
| `WAKE_WORD` | ok | 切回手势唤醒词 |

### DeepSeek 生成

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | "" | API Key（仅内存，不持久化） |
| `DEEPSEEK_MODEL` | deepseek-chat | 模型名 |
| `DEEPSEEK_MAX_TOKENS` | 500 | 每页最大 token |
| `DEEPSEEK_TEMPERATURE` | 0.7 | 创意度(0~1) |
| `SHOW_SPEECH_PROMPTER` | True | 自动显示提词器 |

### 提词器滚动

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SPEECH_ENABLE_SCROLL` | True | 启用自动滚动 |
| `SPEECH_SCROLL_INTERVAL_MS` | 3000 | 滚动间隔(ms) |
| `SPEECH_SCROLL_STEP` | 1 | 每次滚动行数 |
| `SPEECH_SCROLL_PAUSE_SECONDS` | 3 | 手动操作后暂停恢复(s) |

### 其他

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `INITIAL_MODE` | gesture | 初始模式 |
| `PPT_NEXT_KEY` | pagedown | 下一页按键 |
| `PPT_PREV_KEY` | pageup | 上一页按键 |
| `TEXT_MATCH_THRESHOLD` | 0.8 | (预留) 文字匹配阈值，当前使用去标点子串包含匹配，非相似度算法 |
| `GESTURE_KEY_MAP` | (见文件) | (预留) 手势→按键映射表，当前主流程由 main.py 直接调度 |
| `SHOW_HELP` | True | 画面帮助信息 |

## 依赖安装

```bash
pip install -r requirements.txt
```

| 包 | 用途 |
|----|------|
| opencv-python | 摄像头采集 |
| mediapipe 0.10+ | 手部检测 |
| Pillow | 图像处理 |
| numpy | 数学运算 |
| python-pptx | PPTX 解析 |
| vosk | 离线语音识别 |
| pyaudio | 麦克风采集 |
| pywin32 | (仅Windows) 键盘模拟、透明窗口、COM |
| openai 1.0+ | DeepSeek API 调用 |

> **注意**：pyaudio 在 Windows 上可能需要 VC++ 运行时；pywin32 装后需运行 `python -m pywin32_postinstall -install`；numpy 兼容问题可回退 `numpy<2`

## 环境要求

| 功能 | Windows | Linux/macOS |
|------|---------|-------------|
| 手势检测识别 | ✅ | ✅ |
| 语音识别 | ✅ | ✅ |
| PPTX 解析 | ✅ | ✅ |
| 键盘模拟翻页 | ✅ pywin32 | ❌ |
| 透明叠加层 | ✅ pywin32 | ❌ |
| COM 同步 | ✅ pywin32 | ❌ |
| 点击穿透字幕 | ✅ 专属 | ❌ |
| AI 生成 | ✅ 需网络 | ✅ 需网络 |

Python 3.9+，需摄像头和麦克风。

## 技术原理

- **手部检测**：MediaPipe Hand Landmarker（`hand_landmarker.task` 模型，21 关键点）+ 几何规则判断 + 自适应防抖
- **语音识别**：Vosk 离线引擎，支持多个候选路径自动搜索模型
- **PPT 文字匹配**：去标点子串包含匹配（`text_clean in spoken_clean or spoken_clean in text_clean`）
- **AI 演讲稿**：DeepSeek API（兼容 OpenAI SDK），逐页串行生成，60s 超时
- **屏幕叠加**：tkinter 透明窗口 + `overrideredirect` + Windows 扩展样式

## 常见问题

**Q: 语音识别不工作？**  
检查 Vosk 模型是否下载、目录是否包含 `am` 文件夹、pyaudio 是否正常。

**Q: 字幕不显示？**  
仅 Windows + pywin32。Linux 用户可自行改用 xdotool。

**Q: 手势不灵敏？**  
调节 `ADAPTIVE_STABILITY_SECONDS`（越小越快）或 `SWIPE_THRESHOLD`（越小越易触发）。

**Q: API Key 安全问题？**  
Key 仅存内存，不写文件，每次启动重新填写。不要硬编码提交。

**Q: 比心手势不触发？**  
确保拇食指交叉捏合，其余三指伸直。调低 `HEART_STABLE_FRAMES`。

**Q: 提词器不显示？**  
检查 `SHOW_SPEECH_PROMPTER=True`，已生成演讲稿，或按三指切换。

## 许可证

MIT