"""
主程序入口
整合手势识别、语音识别、PPT 控制的完整流程。

运行方式：
    python main.py

启动流程：
    1. 选择 PPTX 文件
    2. 初始化摄像头、手势检测器、语音识别（但不启动监听）、PPT 控制器
    3. 进入主循环，默认手势控制模式
    4. 手势模式：左滑/右滑翻页，OK 手势 → 启动语音识别并切换到语音模式
    5. 语音模式：说出幻灯片文字可高亮，说 'ok' 停止语音并切回手势模式
"""

import os
import re
import sys
import time

# 强制 stdout 使用 UTF-8 编码，避免 emoji 打印报 GBK 错误
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


import cv2
import numpy as np

import config
from hand_detector import HandDetector
from gesture_recognizer import GestureRecognizer
from voice_recognizer import VoiceRecognizer
from ppt_controller import PPTController
from overlay_renderer import OverlayRenderer
from screen_overlay import ScreenOverlay
from settings_panel import SettingsPanel
from speech_generator import generate_speech


def select_pptx_file() -> str:
    """弹出文件选择对话框，选择 PPTX 文件（调用 Windows 原生对话框）"""
    import subprocess, json, tempfile, os
    ps_script = r'''
Add-Type -AssemblyName System.Windows.Forms
$fd = New-Object System.Windows.Forms.OpenFileDialog
$fd.Title = "选择 PPT 文件"
$fd.Filter = "PowerPoint 文件 (*.pptx)|*.pptx|所有文件 (*.*)|*.*"
$fd.ShowDialog() | Out-Null
Write-Output $fd.FileName
'''
    ps_script_path = os.path.join(tempfile.gettempdir(), "filedialog.ps1")
    with open(ps_script_path, "w", encoding="utf-8") as f:
        f.write(ps_script)
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path],
        capture_output=True, text=True, timeout=120
    )
    try:
        os.remove(ps_script_path)
    except:
        pass
    path = result.stdout.strip()
    if path and os.path.isfile(path):
        return path
    return ""


def main():
    print("=" * 60)
    print("  手势 + 语音 PPT 控制器")
    print("=" * 60)

    # ---- 1. 选择 PPT 文件（弹窗选择） ----
    print("\n请选择要控制的 PPTX 文件（文件选择对话框已弹出，请查看任务栏）...")
    ppt_path = select_pptx_file()
    if not ppt_path:
        print("[主程序] 未选择文件，退出。")
        return

    print(f"[主程序] 已选择: {ppt_path}")

    # ---- 2. 初始化 PPT 控制器（需要先加载，供设置面板使用）----
    ppt_ctrl = PPTController(ppt_path)
    if ppt_ctrl.total_pages == 0:
        print("[主程序] 警告: PPT 文件为空或解析失败，将仅有翻页功能无文字匹配。")

    # ---- 3. 弹出设置面板（DeepSeek API Key + 演讲稿生成/编辑）----
    print("\n[主程序] 正在打开设置面板...")
    settings = SettingsPanel(ppt_ctrl)
    result = settings.run()
    if result is None:
        print("[主程序] 用户取消，退出。")
        return

    # 如果有演讲稿，加载到 PPT 控制器
    speech_notes = result.get("speech_notes", {})
    if speech_notes:
        ppt_ctrl.set_speech_notes(speech_notes)
        print(f"[主程序] 已加载 {len(speech_notes)} 页演讲稿")

    # ---- 4. 初始化其他模块 ----
    print("\n[主程序] 正在初始化其他模块...")

    # 手部检测
    detector = HandDetector()
    if not detector.initialize():
        print("[主程序] 手部检测器初始化失败，退出。")
        return

    # 手势识别
    gesture_rec = GestureRecognizer()

    # 语音识别（初始化但不启动监听，按需启动）
    voice_rec = VoiceRecognizer()
    voice_initialized = voice_rec.initialize()
    if not voice_initialized:
        print("[主程序] 语音识别初始化失败（仅手势模式可用）")

    # 叠加渲染
    renderer = OverlayRenderer(
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT
    )

    # 屏幕叠加层（在 PPT 放映画面底部显示实时语音字幕）
    screen_overlay = ScreenOverlay()
    screen_overlay.start()

    # ---- 5. 启动摄像头 ----
    cap = cv2.VideoCapture(config.CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    if not cap.isOpened():
        print("[主程序] 无法打开摄像头，退出。")
        detector.close()
        return

    print("[主程序] 摄像头已开启")

    # ---- 6. 主循环 ----
    current_mode = config.INITIAL_MODE  # "gesture" 或 "voice"
    running = True
    frame_count = 0

    # 注意：默认不启动语音监听！仅在切换到 voice 模式时才启动

    # 防抖：防止同一句语音命令触发多次
    last_voice_turn_time = 0
    last_dir = ""
    VOICE_TURN_COOLDOWN = 1.0  # 翻页防抖间隔（秒）

    # 显示帮助
    cv2.namedWindow("PPT 控制器", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("PPT 控制器", config.CAMERA_WIDTH, config.CAMERA_HEIGHT)

    print("\n" + "=" * 60)
    print("  程序已启动！")
    print(f"  默认模式: {'手势控制' if current_mode == 'gesture' else '语音识别'}")
    print("  ┌──── 手势控制（默认 8 种手势）────┐")
    print("  │ 🤚 手掌右滑 → 下一页               │")
    print("  │ 🤚 手掌左滑 → 上一页               │")
    print("  │ ☝️  伸1指   → 下一页               │")
    print("  │ ✌️  伸2指   → 上一页               │")
    print("  │ 👍 OK手势   → 切换语音模式          │")
    print("  │ 👍 竖大拇指 → 跳转首页              │")
    print("  │ 🖐 五指张开 → 跳转末页              │")
    print("  └──────────────────────────────────┘")
    print("  ┌──── 语音命令（OK手势/按 V 进入）───┐")
    print("  │ 说 '下一页/上一页'  → 翻页           │")
    print("  │ 说 '首页/最后一页'  → 跳转           │")
    print("  │ 说 '黑屏'          → 黑屏/恢复      │")
    print("  │ 说 '结束放映'      → 退出放映       │")
    print("  │ 说 'ok/好的'       → 切回手势模式    │")
    print("  │ 说 PPT上文字        → 字幕显示       │")
    print("  └──────────────────────────────────┘")
    print("  ┌──── 键盘快捷键 ────────────────────┐")
    print("  │ ESC 退出  G 手势  V 语音           │")
    print("  │ N 下一页  P 上一页                  │")
    print("  └──────────────────────────────────┘")
    print("=" * 60 + "\n")

    while running:
        ret, frame = cap.read()
        if not ret:
            print("[主程序] 无法读取摄像头画面")
            break

        frame_count += 1

        # ---- 7. 模式控制逻辑 ----
        if current_mode == "gesture":
            # ---- 手势识别 ----
            result = detector.detect(frame)
            gesture = gesture_rec.recognize(result)

            # 更新覆盖层
            gesture_names = {
                "swipe_left": "👈 左滑翻页",
                "swipe_right": "👉 右滑翻页",
                "ok_gesture": "👍 OK 手势",
                "one_finger": "☝️ 1指→下一页",
                "two_fingers": "✌️ 2指→上一页",
                "thumbs_up": "👍 大拇指→首页",
                "five_fingers": "🖐 五指→末页",
                "three_fingers": "🤟 三指→演讲稿",
                "heart_gesture": "❤️ 比心→标记重点",
            }
            renderer.set_gesture(gesture_names.get(gesture, ""))

            def _show_speech_prompter():
                """翻页后显示当前页演讲稿（如果有）"""
                speech = ppt_ctrl.get_current_speech()
                if speech:
                    screen_overlay.show_speech(speech)
                    print(f"[提词] 第 {ppt_ctrl.get_current_page_number()} 页演讲稿已显示")

            # 处理手势
            if gesture == "swipe_left":
                ppt_ctrl.prev_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                _show_speech_prompter()
            elif gesture == "swipe_right":
                ppt_ctrl.next_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                _show_speech_prompter()
            elif gesture == "one_finger":
                ppt_ctrl.next_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                print(f"[手势] 1指 → 下一页（第 {ppt_ctrl.get_current_page_number()} 页）")
                _show_speech_prompter()
            elif gesture == "two_fingers":
                ppt_ctrl.prev_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                print(f"[手势] 2指 → 上一页（第 {ppt_ctrl.get_current_page_number()} 页）")
                _show_speech_prompter()
            elif gesture == "thumbs_up":
                ppt_ctrl.go_to_first_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                print("[手势] 👍 大拇指 → 首页")
                _show_speech_prompter()
            elif gesture == "five_fingers":
                ppt_ctrl.go_to_last_page()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                )
                print("[手势] 🖐 五指 → 末页")
                _show_speech_prompter()
            elif gesture == "heart_gesture":
                # 比心手势 → 标记当前页为重点页
                ppt_ctrl.mark_current_page_as_key()
                renderer.set_page_info(
                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页 ★"
                )
                print(f"[手势] ❤️ 比心 → 已标记第 {ppt_ctrl.get_current_page_number()} 页为重点页")
            elif gesture == "three_fingers":
                # 三指 → 切换演讲稿显示/隐藏
                screen_overlay.toggle_speech_visibility()
                print("[手势] 🤟 三指 → 切换演讲稿显示")
            elif gesture == "ok_gesture":
                current_mode = "voice"
                renderer.set_mode("voice")
                renderer.set_voice_text("")
                # 切换为语音模式时，启动语音监听
                if voice_initialized:
                    voice_rec.start_listening()
                    screen_overlay.show_subtitle("🎤 语音模式已开启，请说话...")
                print("[主程序] → 切换为语音识别模式（语音监听已启动）")
                # 重置手势识别状态
                gesture_rec.reset()

        else:  # voice 模式
            # ---- 语音识别处理 ----
            if voice_initialized:
                result_item = voice_rec.get_result()
                if result_item:
                    result_type, text = result_item
                    renderer.set_voice_text(text)
                    # 实时字幕：将语音识别结果显示在屏幕底部
                    screen_overlay.show_subtitle(text)

                    # 统一清洗文本：去除非中英文字符、转小写
                    text_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())

                    # --- 检查翻页命令（带防抖，防止 partial 多次触发） ---
                    turned = False
                    now = time.time()
                    is_turn_cmd = False
                    direction = ""
                    if any(kw in text_clean for kw in ["下一页", "下一张", "下页", "往下"]):
                        is_turn_cmd = True
                        direction = "next"
                    elif any(kw in text_clean for kw in ["上一页", "上一张", "上页", "往上"]):
                        is_turn_cmd = True
                        direction = "prev"

                    if is_turn_cmd:
                        # 防抖：1 秒内同一方向不重复翻页
                        if (now - last_voice_turn_time > VOICE_TURN_COOLDOWN or
                            direction != last_dir):
                            last_voice_turn_time = now
                            last_dir = direction
                            if direction == "next":
                                ppt_ctrl.next_page()
                                renderer.set_voice_text(f"→ 下一页")
                                print(f"[语音翻页] 下一页 → 第 {ppt_ctrl.get_current_page_number()} 页")
                            else:
                                ppt_ctrl.prev_page()
                                renderer.set_voice_text(f"← 上一页")
                                print(f"[语音翻页] 上一页 ← 第 {ppt_ctrl.get_current_page_number()} 页")
                            renderer.set_page_info(
                                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                            )
                            # 显示演讲稿
                            speech = ppt_ctrl.get_current_speech()
                            if speech:
                                screen_overlay.show_speech(speech)
                                print(f"[提词] 第 {ppt_ctrl.get_current_page_number()} 页演讲稿已显示")
                        else:
                            print(f"[语音翻页·忽略] 防抖: {now - last_voice_turn_time:.2f}s")
                        turned = True

                    if turned:
                        continue  # 翻页后跳过后续处理

                    # --- 非翻页命令，但检查其他语音控制命令（final 结果） ---
                    if result_type == "final":
                        # 检查是否是唤醒词（切回手势模式）
                        if (text_clean == config.WAKE_WORD or
                            text_clean == "ok" or
                            "好的" in text_clean):
                            current_mode = "gesture"
                            renderer.set_mode("gesture")
                            renderer.set_voice_text("")
                            voice_rec.stop_listening()
                            screen_overlay.clear_subtitle()
                            print("[主程序] ← 切换为手势控制模式（语音监听已停止）")
                            continue

                        # --- 其他语音命令 ---
                        cmd_handled = False

                        # 跳转首页
                        if any(kw in text_clean for kw in ["第一页", "首页", "回到首页", "从头开始"]):
                            ppt_ctrl.go_to_first_page()
                            renderer.set_page_info(
                                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                            )
                            renderer.set_voice_text("→ 首页")
                            print(f"[语音命令] 跳转到首页")
                            cmd_handled = True
                            speech = ppt_ctrl.get_current_speech()
                            if speech:
                                screen_overlay.show_speech(speech)

                        # 跳转末页
                        if any(kw in text_clean for kw in ["最后一页", "末页", "最后"]):
                            ppt_ctrl.go_to_last_page()
                            renderer.set_page_info(
                                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                            )
                            renderer.set_voice_text("→ 末页")
                            print(f"[语音命令] 跳转到末页")
                            cmd_handled = True
                            speech = ppt_ctrl.get_current_speech()
                            if speech:
                                screen_overlay.show_speech(speech)

                        # 黑屏/恢复
                        if any(kw in text_clean for kw in ["黑屏", "关屏", "屏幕关"]):
                            ppt_ctrl.toggle_black_screen()
                            renderer.set_voice_text("■ 黑屏切换")
                            print("[语音命令] 黑屏/恢复")
                            cmd_handled = True

                        # 结束放映
                        if any(kw in text_clean for kw in ["结束放映", "结束", "退出放映"]):
                            ppt_ctrl.quit_show()
                            renderer.set_voice_text("→ 结束放映")
                            print("[语音命令] 结束放映")
                            cmd_handled = True

                        if cmd_handled:
                            continue

                        # 尝试匹配 PPT 文字，在字幕中显示 PPT 原文
                        matched = ppt_ctrl.match_text(text_clean)
                        if matched:
                            matched_ppt_text = matched[0]
                            print(f"[匹配] PPT 文字: {matched_ppt_text}")
                            # 字幕显示匹配到的 PPT 原文内容
                            screen_overlay.show_subtitle(f"� {matched_ppt_text}")
                else:
                    # 显示部分识别结果
                    partial = voice_rec.get_partial_text()
                    if partial:
                        renderer.set_voice_text(partial)
                        # 实时字幕：部分识别结果也显示
                        screen_overlay.show_subtitle(partial)
                        # partial 结果也检查翻页（带防抖，避免重复触发）
                        partial_clean = re.sub(r'[^\w\u4e00-\u9fff]', '', partial.lower())
                        now = time.time()
                        if any(kw in partial_clean for kw in ["下一页", "下一张", "下页", "往下"]):
                            if now - last_voice_turn_time > VOICE_TURN_COOLDOWN:
                                last_voice_turn_time = now
                                last_dir = "next"
                                ppt_ctrl.next_page()
                                renderer.set_page_info(
                                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                                )
                                renderer.set_voice_text(f"→ 下一页")
                                print(f"[语音翻页·partial] 下一页 → 第 {ppt_ctrl.get_current_page_number()} 页")
                                speech = ppt_ctrl.get_current_speech()
                                if speech:
                                    screen_overlay.show_speech(speech)
                        elif any(kw in partial_clean for kw in ["上一页", "上一张", "上页", "往上"]):
                            if now - last_voice_turn_time > VOICE_TURN_COOLDOWN:
                                last_voice_turn_time = now
                                last_dir = "prev"
                                ppt_ctrl.prev_page()
                                renderer.set_page_info(
                                    f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
                                )
                                renderer.set_voice_text(f"← 上一页")
                                print(f"[语音翻页·partial] 上一页 ← 第 {ppt_ctrl.get_current_page_number()} 页")
                                speech = ppt_ctrl.get_current_speech()
                                if speech:
                                    screen_overlay.show_speech(speech)
            else:
                # 没有语音识别，自动切回手势模式
                current_mode = "gesture"
                renderer.set_mode("gesture")
                if voice_initialized:
                    voice_rec.stop_listening()

            # 语音模式下彻底不检测手势，只用语音控制
            # 说 "ok" 或 "好的" 切回手势模式


        # ---- 8. 更新页面信息到覆盖层 ----
        if not renderer.get_page_info() or frame_count % 30 == 0:
            renderer.set_page_info(
                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
            )

        # ---- 9. 渲染并显示 ----
        frame = renderer.render(frame)
        cv2.imshow("PPT 控制器", frame)

        # ---- 10. 处理键盘事件 ----
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            running = False
        elif key == ord('g') or key == ord('G'):
            current_mode = "gesture"
            renderer.set_mode("gesture")
            if voice_initialized:
                voice_rec.stop_listening()
            gesture_rec.reset()
            print("[主程序] ← 手动切换为手势控制模式")
        elif key == ord('v') or key == ord('V'):
            current_mode = "voice"
            renderer.set_mode("voice")
            if voice_initialized:
                voice_rec.start_listening()
            gesture_rec.reset()
            print("[主程序] → 手动切换为语音识别模式")
        elif key == ord('n') or key == ord('N'):
            ppt_ctrl.next_page()
            renderer.set_page_info(
                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
            )
            speech = ppt_ctrl.get_current_speech()
            if speech:
                screen_overlay.show_speech(speech)
        elif key == ord('p') or key == ord('P'):
            ppt_ctrl.prev_page()
            renderer.set_page_info(
                f"第 {ppt_ctrl.get_current_page_number()}/{ppt_ctrl.get_total_pages()} 页"
            )
            speech = ppt_ctrl.get_current_speech()
            if speech:
                screen_overlay.show_speech(speech)
        elif key == ord('r') or key == ord('R'):
            # 按 R 键 → 生成并打印重点页报告
            report = ppt_ctrl.generate_key_pages_report()
            print("\n" + report + "\n")
            # 同时在屏幕显示
            screen_overlay.show_subtitle("📋 重点页报告已生成（见控制台）")

    # ---- 11. 清理资源 ----
    cap.release()
    cv2.destroyAllWindows()
    detector.close()
    if voice_initialized:
        voice_rec.close()
    screen_overlay.stop()
    print("\n[主程序] 程序已退出。")


if __name__ == "__main__":
    main()