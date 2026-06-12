"""
设置面板模块
在选择 PPTX 文件后弹出 tkinter 窗口：
1. 配置 DeepSeek API Key 和模型
2. 预览/编辑各页演讲稿
3. 确认后进入演示模式
"""

import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

import config
from speech_generator import generate_batch


class SettingsPanel:
    """启动前的设置面板窗口"""

    def __init__(self, ppt_ctrl):
        """
        Args:
            ppt_ctrl: PPTController 实例（已加载 PPTX）
        """
        self.ppt_ctrl = ppt_ctrl
        self.result = None  # 关闭时保存最终配置

        # 演讲稿缓存 {页码(0-based): str}
        self.speech_notes: dict[int, str] = {}
        self.current_page_idx = 0

        # 是否为编辑状态（未生成时手动填写）
        self._editing = False

        # 创建窗口
        self.root = tk.Tk()
        self.root.title("📋 演讲稿设置面板")
        self.root.geometry("780x680")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # 初始化 UI
        self._build_ui()

        # 自动填入已保存的 API Key
        saved_key = config.DEEPSEEK_API_KEY
        if saved_key:
            self.api_key_var.set(saved_key)

    def _build_ui(self):
        """构建界面"""

        # ========== 顶部：API 配置区 ==========
        config_frame = ttk.LabelFrame(self.root, text=" DeepSeek API 配置 ", padding=10)
        config_frame.pack(fill="x", padx=10, pady=(10, 5))

        # API Key 行
        key_row = ttk.Frame(config_frame)
        key_row.pack(fill="x", pady=2)
        ttk.Label(key_row, text="API Key:").pack(side="left")
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(
            key_row, textvariable=self.api_key_var, width=50, show="*"
        )
        self.api_key_entry.pack(side="left", padx=5, fill="x", expand=True)
        self._toggle_btn = ttk.Button(
            key_row, text="👁", width=3, command=self._toggle_api_key_visibility
        )
        self._toggle_btn.pack(side="left", padx=2)

        # 模型选择行
        model_row = ttk.Frame(config_frame)
        model_row.pack(fill="x", pady=2)
        ttk.Label(model_row, text="模型:").pack(side="left")
        self.model_var = tk.StringVar(value=config.DEEPSEEK_MODEL)
        self.model_combo = ttk.Combobox(
            model_row, textvariable=self.model_var,
            values=["deepseek-chat", "deepseek-reasoner"],
            width=20, state="readonly"
        )
        self.model_combo.pack(side="left", padx=5)
        ttk.Label(model_row, text="Token限制:").pack(side="left", padx=(20, 0))
        self.max_tokens_var = tk.IntVar(value=config.DEEPSEEK_MAX_TOKENS)
        self.max_tokens_spin = ttk.Spinbox(
            model_row, from_=100, to=2000, textvariable=self.max_tokens_var,
            width=8
        )
        self.max_tokens_spin.pack(side="left", padx=5)
        ttk.Label(model_row, text="创意度:").pack(side="left", padx=(20, 0))
        self.temperature_var = tk.DoubleVar(value=config.DEEPSEEK_TEMPERATURE)
        self.temp_scale = ttk.Scale(
            model_row, from_=0.0, to=1.0, variable=self.temperature_var,
            orient="horizontal", length=100
        )
        self.temp_scale.pack(side="left", padx=5)
        self.temp_label = ttk.Label(model_row, text="0.7")
        self.temp_label.pack(side="left")
        self.temperature_var.trace_add("write", lambda *a: self.temp_label.config(
            text=f"{self.temperature_var.get():.1f}"
        ))

        # 生成按钮行
        gen_row = ttk.Frame(config_frame)
        gen_row.pack(fill="x", pady=(5, 0))
        self.gen_btn = ttk.Button(
            gen_row, text="🔄 生成全部演讲稿", command=self._generate_all, width=25
        )
        self.gen_btn.pack(side="left", padx=5)
        self.progress_label = ttk.Label(gen_row, text="", foreground="#888")
        self.progress_label.pack(side="left", padx=10)
        self.progress_bar = ttk.Progressbar(
            gen_row, mode="determinate", length=200
        )
        self.progress_bar.pack(side="left", padx=5)

        # ========== 中间：预览/编辑区 ==========
        preview_frame = ttk.LabelFrame(self.root, text=" 演讲稿预览与编辑 ", padding=5)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左右分栏
        paned = ttk.PanedWindow(preview_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 左侧：页码列表
        left_frame = ttk.Frame(paned, width=120)
        paned.add(left_frame, weight=0)

        page_label = ttk.Label(left_frame, text="幻灯片列表", font=("", 10, "bold"))
        page_label.pack(pady=2)

        self.page_listbox = tk.Listbox(
            left_frame, width=15, font=("Microsoft YaHei", 11),
            selectmode="single", activestyle="none"
        )
        self.page_listbox.pack(fill="both", expand=True, padx=2, pady=2)
        self.page_listbox.bind("<<ListboxSelect>>", self._on_page_select)

        # 填充页码列表
        for i in range(self.ppt_ctrl.total_pages):
            texts = self.ppt_ctrl.page_texts.get(i, [])
            first_line = texts[0][:15] if texts else "(空白)"
            self.page_listbox.insert(tk.END, f"📄 第{i+1}页  {first_line}")

        # 右侧：演讲稿编辑区
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        self.speech_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 12),
            padx=5, pady=5,
            height=15
        )
        self.speech_text.pack(fill="both", expand=True, padx=2, pady=2)
        self.speech_text.bind("<KeyRelease>", self._on_edit_speech)

        # 底部提示
        tip_label = ttk.Label(
            right_frame,
            text="💡 可直接编辑上方文本框修改演讲稿",
            foreground="#888", font=("", 9)
        )
        tip_label.pack(anchor="w", padx=5)

        # ========== 底部：操作按钮 ==========
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.status_label = ttk.Label(
            btn_frame,
            text=f"共 {self.ppt_ctrl.total_pages} 页，未生成演讲稿",
            foreground="#888"
        )
        self.status_label.pack(side="left")

        # 跳过生成/直接进入
        self.skip_btn = ttk.Button(
            btn_frame, text="⏩ 跳过生成，直接开始",
            command=self._on_skip
        )
        self.skip_btn.pack(side="right", padx=5)

        ttk.Button(
            btn_frame, text="✅ 开始演示",
            command=self._on_confirm
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame, text="✕ 取消",
            command=self._on_cancel
        ).pack(side="right", padx=5)

    # ==================== 事件处理 ====================

    def _toggle_api_key_visibility(self):
        """切换 API Key 可见性"""
        if self.api_key_entry.cget("show") == "*":
            self.api_key_entry.config(show="")
            self._toggle_btn.config(text="🙈")
        else:
            self.api_key_entry.config(show="*")
            self._toggle_btn.config(text="👁")

    def _generate_all(self):
        """生成全部演讲稿（在新线程中执行，避免阻塞 UI）"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "请先填写 DeepSeek API Key")
            return

        if self.ppt_ctrl.total_pages == 0:
            messagebox.showwarning("提示", "PPT 文件为空，无需生成")
            return

        # 禁用按钮
        self.gen_btn.config(state="disabled")
        self.progress_bar["maximum"] = self.ppt_ctrl.total_pages
        self.progress_bar["value"] = 0
        self.progress_label.config(text="准备中...", foreground="#333")

        def callback(page_num, total, msg):
            """进度回调（在 UI 线程执行）"""
            self.root.after(0, lambda: self._update_progress(page_num, total, msg))

        def worker():
            """后台线程执行生成"""
            texts_by_page = self.ppt_ctrl.page_texts
            result = generate_batch(
                texts_by_page=texts_by_page,
                api_key=api_key,
                model=self.model_var.get(),
                max_tokens=self.max_tokens_var.get(),
                temperature=self.temperature_var.get(),
                progress_callback=callback
            )
            self.root.after(0, lambda: self._on_generate_done(result))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _update_progress(self, page_num, total, msg):
        """更新进度显示"""
        self.progress_bar["value"] = page_num
        self.progress_label.config(text=msg, foreground="#333")
        self.status_label.config(
            text=f"正在生成... {page_num}/{total} 页"
        )

    def _on_generate_done(self, result: dict):
        """生成完成回调"""
        self.speech_notes = result
        self.gen_btn.config(state="normal")
        self.progress_label.config(text="✅ 生成完成", foreground="green")

        # 显示第一页的演讲稿
        if result:
            self.current_page_idx = 0
            self.page_listbox.selection_clear(0, tk.END)
            self.page_listbox.selection_set(0)
            self.page_listbox.activate(0)
            self._show_speech_for_page(0)

        # 统计成功/失败
        total = len(result)
        fails = sum(1 for v in result.values() if "失败" in v or "错误" in v)
        success = total - fails
        self.status_label.config(
            text=f"✅ 生成完成：{success} 页成功"
                  + (f"，{fails} 页失败" if fails else "")
        )

    def _show_speech_for_page(self, page_idx: int):
        """在编辑区显示指定页的演讲稿"""
        self._editing = False
        self.speech_text.delete("1.0", tk.END)
        speech = self.speech_notes.get(page_idx, "")
        if speech:
            self.speech_text.insert("1.0", speech)
        else:
            # 显示默认占位符
            texts = self.ppt_ctrl.page_texts.get(page_idx, [])
            if texts:
                self.speech_text.insert(
                    "1.0",
                    f'（第 {page_idx + 1} 页尚未生成演讲稿，点击\u201c生成全部\u201d或手动填写）'
                )
            else:
                self.speech_text.insert(
                    "1.0",
                    f"（第 {page_idx + 1} 页无文字内容）"
                )

    def _on_page_select(self, event):
        """切换页码选择"""
        selection = self.page_listbox.curselection()
        if not selection:
            return
        page_idx = selection[0]
        self.current_page_idx = page_idx

        # 保存当前编辑内容
        if self._editing:
            current_text = self.speech_text.get("1.0", tk.END).strip()
            if current_text:
                self.speech_notes[self.current_page_idx] = current_text

        self._show_speech_for_page(page_idx)

    def _on_edit_speech(self, event=None):
        """演讲稿被用户编辑"""
        self._editing = True
        # 实时保存到缓存
        current_text = self.speech_text.get("1.0", tk.END).strip()
        if current_text:
            self.speech_notes[self.current_page_idx] = current_text

    def _on_confirm(self):
        """确认，开始演示"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            if not messagebox.askyesno(
                "确认", "未填写 DeepSeek API Key，将无法自动生成演讲稿。继续吗？"
            ):
                return

        # 保存当前编辑内容
        if self._editing:
            current_text = self.speech_text.get("1.0", tk.END).strip()
            if current_text:
                self.speech_notes[self.current_page_idx] = current_text

        # 保存 API Key 到 config
        if api_key:
            config.DEEPSEEK_API_KEY = api_key
            config.DEEPSEEK_MODEL = self.model_var.get()
            config.DEEPSEEK_MAX_TOKENS = self.max_tokens_var.get()
            config.DEEPSEEK_TEMPERATURE = self.temperature_var.get()

        self.result = {
            "speech_notes": self.speech_notes,
            "api_key": api_key,
            "model": self.model_var.get(),
        }
        self.root.destroy()

    def _on_skip(self):
        """跳过生成，直接开始演示"""
        self.speech_notes = {}
        self.result = {
            "speech_notes": {},
            "api_key": "",
            "model": self.model_var.get(),
        }
        self.root.destroy()

    def _on_cancel(self):
        """取消"""
        self.result = None
        self.root.destroy()

    # ==================== 运行 ====================

    def run(self) -> dict | None:
        """运行设置面板，返回配置结果（阻塞）"""
        self.root.mainloop()
        return self.result