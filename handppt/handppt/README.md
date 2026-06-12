# 手势 + 语音 PPT 控制器

基于 **MediaPipe 手部检测** + **Vosk 离线语音识别** + **DeepSeek AI 演讲稿生成**，通过手势、语音或键盘控制 PPT 翻页，支持 AI 自动生成演讲稿并滚动显示（提词器）。

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 下载 MediaPipe 手部检测模型
#    下载地址：https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
#    将 hand_landmarker.task 放到 handppt/ 目录下（与 hand_detector.py 同目录）

# 3. 下载 Vosk 中文语音模型
#    下载地址：https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip
#    解压后找到包含 "am" 文件夹的目录，放到项目根目录，
#    目录名设置为 vosk-model-cn-0.22
#    （程序会自动查找 vosk-model-cn-0.22、model 等候选路径，
#     并递归搜索 am 子目录）

# 4. 启动
python main.py
```

> **可选功能**：如需 AI 演讲稿生成，需注册 [DeepSeek](https://platform.deepseek.com/) 获取 API Key（格式：`sk-xxx...`），在弹出设置面板中填入即可。

> **键盘控制**：兼容 PowerPoint / WPS —— 所有控制通过模拟键盘按键实现（需要 pywin32，仅 Windows）。

---

## 启动流程

```
启动 → 选择 PPTX 文件 → 弹出演讲稿设置面板(tkinter)
       ├─ 填入 DeepSeek API Key + 选择模型
       ├─ 点击"生成全部演讲稿" → 逐页调用 DeepSeek API → 预览区显示结果
       ├─ 可双击每一页手动编辑演讲稿
       ├─ 点击"开始演示" → 进入摄像头 + 手势控制
       └─ 每次翻页 → 底部自动滚动显示当前页演讲稿
```

---

## 功能亮点

| 特性 | 说明 |
|------|------|
| **🖐 手势控制** | 9 种手势：左右滑翻页、伸 1/2 指翻页、OK 切语音、大拇指首页、五指末页、比心标记、三指切换提词器 |
| **🎤 语音控制** | 离线中文语音识别，支持翻页、跳转、黑屏、结束放映、切回手势、PPT 文字匹配字幕 |
| **🤖 AI 演讲稿生成** | 接入 DeepSeek API，逐页生成口语化演讲稿，支持手动编辑 |
| **📜 演讲稿提词器** | 翻页后底部自动显示当前页演讲稿，跑马灯横向滚动，0.5 秒淡入动画 |
| **❤️ 重点页标记** | 比心手势将当前页标为重点页，按 R 键生成重点页报告 |
| **💬 实时字幕** | 语音识别结果实时显示在 PPT 放映画面底部（黑色背景条 + 白色文字） |
| **⌨️ 键盘快捷键** | ESC 退出、G 手势/V 语音、N 下一页/P 上一页、R 重点页报告 |
| **🔁 动态模式切换** | 默认手势模式，比 OK 手势进入语音模式，说"ok"回到手势，双向无缝切换 |
| **📌 点击穿透字幕** | tkinter 置顶透明窗口，不干扰 PPT 鼠标操作 |
| **🛡️ 防误触** | 连续稳定多帧后触发 + 翻页防抖冷却，自适应帧率稳定算法 |

---

## 全部功能对照表

### 手势控制（默认进入）

| 手势 | 动作描述 | 效果 |
|------|---------|------|
| 🤚 手掌**右滑** | 五指张开向右水平滑动 | **下一页** |
| 🤚 手掌**左滑** | 五指张开向左水平滑动 | **上一页** |
| ☝️ **伸 1 指** | 只有食指伸直 | **下一页** |
| ✌️ **伸 2 指** | 食指+中指伸直 | **上一页** |
| 👍 **OK 手势** | 拇指+食指捏合成圈，其余三指张开 | **切换到语音模式** |
| 👍 **竖大拇指** | 拇指伸直，其余四指弯曲 | **跳到首页** |
| 🖐 **五指张开** | 所有手指伸直张开 | **跳到末页** |
| ❤️ **比心手势** | 拇指+食指尖交叉捏合，其余三指张开 | **标记当前页为重点页**（显示★） |
| 🤟 **三指手势** | 食指+中指+无名指竖起，小指弯曲 | **切换演讲稿提词器 显示/隐藏** |

### 语音控制（OK 手势进入）

| 说出的话 | 效果 |
|---------|------|
| **"下一页" / "下一张" / "往下"** | **下一页** |
| **"上一页" / "上一张" / "往上"** | **上一页** |
| **"首页" / "第一页" / "从头开始"** | **跳到第 1 页** |
| **"末页" / "最后一页"** | **跳到最后一页** |
| **"黑屏" / "关屏"** | **黑屏 / 恢复显示** |
| **"结束放映" / "退出放映"** | **退出全屏放映** |
| **"ok" / "好的"** | **切回手势控制模式** |
| **PPT 上的文字**（如"项目背景"） | **底部字幕显示匹配到的 PPT 原文** |

### 键盘快捷键

| 按键 | 效果 |
|------|------|
| **ESC** | 退出程序 |
| **G** | 手动切回手势模式 |
| **V** | 手动切到语音模式 |
| **N** | 手动下一页 |
| **P** | 手动上一页 |
| **R** | 生成并打印重点页报告 |

---

## AI 演讲稿生成

本功能通过 DeepSeek Chat API（兼容 OpenAI SDK）逐页生成口语化演讲稿。

### 使用方法

1. 启动程序 -> 选择 PPTX 文件 -> 弹出设置面板
2. 填入 DeepSeek API Key（格式：`sk-xxx...`），选择模型
3. 点击"生成全部演讲稿" — 逐页调用 API，进度条实时显示
4. 生成完成后可在预览区双击编辑任意页演讲稿
5. 点击"开始演示"进入控制模式

### 重要提示

- **API Key 仅存储在内存中** — 设置面板填入的 Key 仅传递给 `config.DEEPSEEK_API_KEY`（内存变量），不会写入磁盘文件。每次启动程序需重新填写。
- **费用提示**：DeepSeek Chat API 按 token 计费，每页演讲稿约消耗 500~1000 token，请参考 [DeepSeek 定价页面](https://platform.deepseek.com/usage)
- **超时处理**：单页生成默认 60 秒超时，失败后可在设置面板手动编辑作为备选
- **速率限制**：批量生成时逐页串行调用，避免触发 API 速率限制
- **Fallback 支持**：API 调用失败时仍可手动在面板中编辑演讲稿，不影响演示
- ⚠️ **不要把 API Key 硬编码写入 `config.py` 并提交到公开仓库！**

---

## 配置说明

所有可调参数集中在 `config.py` 中，以下为完整参数说明：

### 摄像头

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_ID` | 0 | 摄像头编号 |
| `CAMERA_WIDTH` | 640 | 摄像头画面宽度 |
| `CAMERA_HEIGHT` | 480 | 摄像头画面高度 |

### 手势识别

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SWIPE_THRESHOLD` | 80 | 滑动触发阈值（像素） |
| `SWIPE_COOLDOWN_SECONDS` | 2.0 | 翻页冷却时间（秒） |
| `ADAPTIVE_STABILITY_SECONDS` | 0.2 | 自适应稳定时长（秒） |
| `ADAPTIVE_COOLDOWN_FRAMES` | 6 | 自适应冷却帧数（帧） |
| `OK_GESTURE_DISTANCE_THRESHOLD` | 40 | OK 手势判定阈值 |
| `FIST_STABLE_FRAMES` | 8 | 握拳稳定帧数 |
| `THUMBS_UP_STABLE_FRAMES` | 8 | 竖大拇指稳定帧数 |
| `FIVE_FINGERS_STABLE_FRAMES` | 6 | 五指张开稳定帧数 |
| `HEART_STABLE_FRAMES` | 10 | 比心手势稳定帧数 |
| `THREE_FINGERS_STABLE_FRAMES` | 8 | 三指手势稳定帧数 |

### 语音识别

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `VOSK_MODEL_DIR` | `vosk-model-cn-0.22` | Vosk 模型目录名（程序会递归搜索包含 am 子目录的路径） |
| `SAMPLE_RATE` | 16000 | 采样率 |
| `SILENCE_TIMEOUT` | 2.0 | 静默超时（秒） |
| `WAKE_WORD` | `ok` | 切回手势模式的唤醒词 |

### DeepSeek 演讲稿生成

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | `""` | DeepSeek API Key（内存存储，不持久化） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名称 |
| `DEEPSEEK_MAX_TOKENS` | 500 | 每页最大 token 数 |
| `DEEPSEEK_TEMPERATURE` | 0.7 | 创意度（0=严谨，1=创意） |
| `SHOW_SPEECH_PROMPTER` | True | 翻页时自动显示提词器 |

### 提词器滚动

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SPEECH_ENABLE_SCROLL` | True | 是否启用自动滚动 |
| `SPEECH_SCROLL_INTERVAL_MS` | 3000 | 滚动间隔（毫秒） |
| `SPEECH_SCROLL_STEP` | 1 | 每次滚动行数 |
| `SPEECH_SCROLL_PAUSE_SECONDS` | 3 | 手动操作后暂停恢复时间（秒） |

### 其他

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `INITIAL_MODE` | `gesture` | 初始模式（gesture / voice） |
| `PPT_NEXT_KEY` | `pagedown` | 下一页按键 |
| `PPT_PREV_KEY` | `pageup` | 上一页按键 |
| `TEXT_MATCH_THRESHOLD` | 0.8 | PPT 文字匹配阈值（预留，当前使用子串匹配，未使用相似度算法） |
| `GESTURE_KEY_MAP` | (详见表) | 手势→按键映射表（预留/备用，当前未集成到主流程。主流程由 main.py 直接 dispatch） |
| `SHOW_HELP` | True | 画面显示帮助信息 |

---

## 技术原理

### 手部检测 & 手势识别

1. **MediaPipe Hand Landmarker** — 基于 `hand_landmarker.task` 模型文件，每帧检测手部 21 个关键点（landmark）的 3D 坐标
2. **模型文件**：下载 `hand_landmarker.task`（约 14MB）放到 `handppt/` 目录。下载地址：`https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task`
3. **几何规则判断** — 通过指尖与指根的坐标关系判定每根手指的弯曲/伸直状态
4. **方向识别** — 手掌中心点连续 N 帧水平位移超过阈值则判定为左滑/右滑
5. **自适应防抖** — 稳定帧数 = `max(3, FPS × 0.2s)`，无论帧率高低都能保持约 0.2 秒确认时间
6. **9 种手势识别**：
   - 滑动翻页（左/右）
   - 数字指法（1 指→下一页，2 指→上一页）
   - OK 手势（拇指+食指捏合，其余三指张开）
   - 全局手势（竖大拇指、五指张开、三指）
   - 比心手势（拇指+食指交叉捏合，其余三指张开）
   - 三指手势（食指+中指+无名指竖起）

### 语音识别

1. **Vosk 离线语音识别** — 本地运行，无需联网，支持中文
2. **模型搜索路径**：程序会依次检查 `vosk-model-cn-0.22`、`vosk-model-small-cn-0.22`、`model` 等候选目录，并递归搜索包含 `am` 文件夹的子目录，支持嵌套解压结构
3. **双模式输出** — partial（部分识别结果，实时显示）+ final（最终结果，用于命令处理）
4. **翻页防抖** — 同一方向翻页命令 1 秒内不重复触发
5. **多关键词匹配** — 每句命令支持多个同义词

### PPT 文字匹配

1. **python-pptx** — 启动时解析 PPTX 所有幻灯片文字 + 位置信息
2. **去标点子串匹配** — 去除标点/空格/大小写后，检查语音文本与 PPT 文本是否为子串包含关系（`text_clean in spoken_clean or spoken_clean in text_clean`）。此为基于字符串包含的判断，非相似度算法；`TEXT_MATCH_THRESHOLD` 参数预留用于未来升级为模糊匹配（如 rapidfuzz）
3. **字幕显示** — 匹配到的 PPT 原文会显示在屏幕底部字幕条中

### AI 演讲稿生成

1. **DeepSeek Chat API** — 兼容 OpenAI SDK，通过 `openai` 库调用（`base_url="https://api.deepseek.com"`）
2. **逐页生成** — 将每页幻灯片文字构造成提示词，生成口语化演讲稿
3. **批量进度** — `generate_batch()` 支持逐页回调更新 UI 进度条
4. **可编辑** — 生成的演讲稿可在设置面板中手动修改

### 屏幕叠加层（提词器 + 字幕）

1. **tkinter 透明窗口** — `overrideredirect(True)` + 透明色键实现全屏透明覆盖
2. **置顶 + 点击穿透** — Windows 扩展样式实现（依赖 pywin32，仅 Windows）
3. **跑马灯演讲稿** — 底部 120px 半透明黑色条，文字横向滚动
4. **语音字幕** — 独立区域显示语音识别结果
5. **淡入动画** — `after()` 定时器驱动 alpha 过渡（0.5 秒）
6. **线程安全队列** — 锁保护的命令队列进行跨线程通信

### PPT 控制

1. **模拟键盘按键** — `win32api.keybd_event` 发送标准快捷键（依赖 pywin32，仅 Windows）
2. **COM 同步页码** — 可选通过 PowerPoint COM 接口获取实际页码（依赖 pywin32，仅 Windows）
3. **页码追踪** — 内部维护 0-based 计数器 + 边界限制

### 重点页标记

1. **比心手势触发** — 10 帧稳定 + 3 秒冷却防误触
2. **内部集合存储** — `set[int]` 记录标记的页码
3. **R 键报告** — 生成包含内容摘要 + 演讲稿预览的格式化报告

---

## 环境要求

| 功能 | Windows | Linux / macOS |
|------|---------|---------------|
| 手势检测 & 识别 | ✅ | ✅ |
| 语音识别（Vosk） | ✅ | ✅ |
| PPTX 文字解析 | ✅ | ✅ |
| 键盘模拟翻页（`_press_key`） | ✅ 需要 pywin32 | ❌ 不可用（pywin32 不可用，`_press_key` 静默失效，无备用方案） |
| 屏幕透明叠加层（提词器 + 字幕） | ✅ 需要 pywin32 | ❌ 不可用（tkinter 透明窗口依赖 win32gui/win32con） |
| PowerPoint COM 同步页码 | ✅ 需要 pywin32 | ❌ 不可用（COM 为 Windows 专属） |
| 点击穿透字幕窗口 | ✅ Windows 专属 | ❌ 不可用 |
| AI 演讲稿生成 | ✅ 需要网络 | ✅ 需要网络 |

- **Python 版本**：3.9+
- **操作系统**：Windows（推荐，功能完整）+ Linux/macOS（手势/语音检测和 PPTX 解析可用，键盘模拟和字幕窗口不可用）
- **摄像头**：USB 或内置摄像头
- **麦克风**：用于语音识别
- **PowerPoint 或 WPS**：用于放映 PPTX 文件
- **网络**（可选）：AI 演讲稿生成需要 DeepSeek API 网络连接

---

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖清单：

| 包名 | 版本 | 用途 |
|------|------|------|
| opencv-python | 4.13+ | 摄像头采集、图像处理 |
| mediapipe | 0.10+ | 手部关键点检测 |
| Pillow | 12.2+ | 图像处理辅助 |
| numpy | 2.4+ | 数学运算 |
| python-pptx | 1.0+ | PPTX 文件解析，提取幻灯片文字 |
| vosk | 0.3+ | 离线中文语音识别 |
| pyaudio | 0.2+ | 麦克风音频采集 |
| pywin32 | — | Windows API 调用（字幕透明窗口、键盘模拟、COM 同步） |
| openai | 1.0+ | DeepSeek / OpenAI API 调用（演讲稿生成） |

> **安装注意事项**：
> - 使用 `pip install -r requirements.txt` 一键安装所有依赖
> - **pyaudio** 在 Windows 上可能需要预先安装 Visual C++ 运行时或使用 wheel 包
> - **pywin32** 仅支持 Windows，安装后可能需要运行 `python -m pywin32_postinstall -install` 完成注册
> - **mediapipe 0.10.x** 需要 Task API 兼容版本，推荐 `0.10.35`
> - **numpy 版本兼容性**：mediapipe 0.10.35 兼容 numpy 1.x 和 2.x，如遇兼容问题可回退到 `numpy<2`

---

## 常见问题

### 1. 摄像头无法打开
检查摄像头是否被其他程序占用，在 `config.py` 中修改 `CAMERA_ID`（尝试 0、1、2）。

### 2. 语音识别不工作
- 已下载 Vosk 中文模型并解压到项目根目录
- 麦克风已正常连接并可被 Python 访问（检查 pyaudio 安装）
- 模型目录名与 `config.py` 中 `VOSK_MODEL_DIR` 一致
- 程序会自动搜索 `vosk-model-cn-0.22`、`vosk-model-small-cn-0.22`、`model` 等候选路径，并递归查找包含 `am` 文件夹的子目录。如果模型解压后出现嵌套目录（如 `vosk-model-cn-0.22/vosk-model-cn-0.22/`），保留内层目录即可

### 3. PPT 文字无法匹配
- 确保 PPTX 中的文字是**可编辑文本框**（不是图片中或 SmartArt 中内嵌的文本）
- 语音识别的准确率受麦克风质量影响，建议在安静环境下使用
- 匹配方式是**去标点子串包含匹配**（非相似度算法）—— 说出的文字是 PPT 文字的子集或超集即可匹配

### 4. 字幕窗口不显示
- 需要 `pywin32` 包支持透明窗口样式（仅 Windows）
- 如果使用 WPS，确保放映窗口为全屏模式
- **非 Windows 用户**：字幕/提词器窗口功能不可用。Linux 用户可考虑用 `xdotool` 替代键盘模拟（需自行修改 `_press_key()` 实现）

### 5. 手势识别不灵敏
- 保证手部在摄像头画面中完整可见
- 调节 `config.py` 中 `ADAPTIVE_STABILITY_SECONDS`（值越小越灵敏）
- 调节 `SWIPE_THRESHOLD`（值越小滑动越易触发）

### 6. AI 演讲稿生成失败
- 确认 DeepSeek API Key 填写正确（格式：`sk-xxx...`）
- 检查网络连接能否访问 `api.deepseek.com`
- 可在设置面板中手动编辑演讲稿作为备选
- API Key 仅存储在内存中，不会写入磁盘，每次启动需重新填写

### 7. 比心手势不触发
- 确保拇指和食指指尖完全交叉捏合，其余三指张开伸直
- 默认需要 10 帧稳定，可在 `config.py` 中调低 `HEART_STABLE_FRAMES`

### 8. 演讲稿提词器不显示
- 检查 `config.py` 中 `SHOW_SPEECH_PROMPTER` 是否为 `True`
- 确认已通过设置面板生成演讲稿
- 尝试 🤟 三指手势切换显示/隐藏

---

## 许可证

MIT License