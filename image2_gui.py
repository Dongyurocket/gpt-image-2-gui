# -*- coding: utf-8 -*-
"""
Tkinter GUI for the gpt-image-2 Images API.

Features:
- Text-to-image via /v1/images/generations
- Image edit / image-to-image via /v1/images/edits
- Saves base URL, API key, output folder, and common options to config.json
- Automatically downloads URL results or decodes b64_json results
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import queue
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime for end users
    requests = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - handled at runtime for end users
    Image = None


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG: dict[str, str] = {
    "base_url": "https://www.packyapi.com",
    "api_key": "",
    "model": "gpt-image-2",
    "size": "1024x1024",
    "quality": "high",
    "output_format": "png",
    "response_format": "url",
    "output_compression": "90",
    "background": "",
    "moderation": "",
    "input_fidelity": "high",
    "output_dir": "outputs",
    "proxy_mode": "不使用代理",
    "proxy_url": "",
    "edit_preprocess": "开启",
    "edit_max_side": "1024",
}

SIZES = [
    "auto",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "1536x864",
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
]

QUALITIES = ["auto", "low", "medium", "high"]
OUTPUT_FORMATS = ["png", "jpeg"]
RESPONSE_FORMATS = ["url", "b64_json"]
OPTIONAL_DEFAULT = ["", "auto", "low"]
BACKGROUND_OPTIONS = ["", "opaque", "auto"]
INPUT_FIDELITY_OPTIONS = ["", "high"]
PROXY_MODES = ["不使用代理", "使用系统代理", "自定义代理"]
PREPROCESS_MODES = ["开启", "关闭"]


class Image2Gui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("gpt-image-2-gui")
        self.geometry("980x760")
        self.minsize(860, 620)

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.buttons: list[ttk.Button] = []

        self.config_values = load_config()
        self.vars = {
            key: tk.StringVar(value=value)
            for key, value in self.config_values.items()
        }
        self.text_prompt: tk.Text | None = None
        self.edit_prompt: tk.Text | None = None
        self.image_paths: list[str] = []
        self.image_count = tk.StringVar(value="尚未选择图片")
        self.image_listbox: tk.Listbox | None = None
        self.mask_path = tk.StringVar()
        self.last_file = tk.StringVar(value="尚未生成图片")

        self._build_ui()
        self._poll_events()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=12)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        root.rowconfigure(4, weight=1)

        connection = ttk.LabelFrame(root, text="连接配置", padding=10)
        connection.grid(row=0, column=0, sticky="ew")
        connection.columnconfigure(1, weight=1)
        connection.columnconfigure(3, weight=1)

        ttk.Label(connection, text="Base URL").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=self.vars["base_url"]).grid(row=0, column=1, sticky="ew", padx=(0, 12))

        ttk.Label(connection, text="API Key").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=self.vars["api_key"], show="*").grid(row=0, column=3, sticky="ew")

        ttk.Label(connection, text="Model").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(connection, textvariable=self.vars["model"]).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(8, 0))

        save_btn = ttk.Button(connection, text="保存配置", command=self.save_config)
        save_btn.grid(row=1, column=3, sticky="e", pady=(8, 0))

        ttk.Label(connection, text="代理模式").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Combobox(
            connection,
            textvariable=self.vars["proxy_mode"],
            values=PROXY_MODES,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=(8, 0))

        ttk.Label(connection, text="代理地址").grid(row=2, column=2, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(connection, textvariable=self.vars["proxy_url"]).grid(row=2, column=3, sticky="ew", pady=(8, 0))

        settings = ttk.LabelFrame(root, text="通用参数", padding=10)
        settings.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for column in range(8):
            settings.columnconfigure(column, weight=1 if column % 2 else 0)

        self._combo(settings, "尺寸", "size", SIZES, 0, 0)
        self._combo(settings, "质量", "quality", QUALITIES, 0, 2)
        self._combo(settings, "输出格式", "output_format", OUTPUT_FORMATS, 0, 4)
        self._combo(settings, "返回格式", "response_format", RESPONSE_FORMATS, 0, 6)
        self._entry(settings, "JPEG压缩", "output_compression", 1, 0)
        self._combo(settings, "背景", "background", BACKGROUND_OPTIONS, 1, 2)
        self._combo(settings, "审核", "moderation", OPTIONAL_DEFAULT, 1, 4)
        self._combo(settings, "保真度", "input_fidelity", INPUT_FIDELITY_OPTIONS, 1, 6)

        ttk.Label(settings, text="输出目录").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(settings, textvariable=self.vars["output_dir"]).grid(row=2, column=1, columnspan=6, sticky="ew", pady=(8, 0))
        ttk.Button(settings, text="选择", command=self.choose_output_dir).grid(row=2, column=7, sticky="ew", padx=(8, 0), pady=(8, 0))

        self._combo(settings, "编辑预处理", "edit_preprocess", PREPROCESS_MODES, 3, 0)
        self._entry(settings, "上传最长边", "edit_max_side", 3, 2)

        tabs = ttk.Notebook(root)
        tabs.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

        text_tab = ttk.Frame(tabs, padding=10)
        text_tab.columnconfigure(0, weight=1)
        text_tab.rowconfigure(1, weight=1)
        tabs.add(text_tab, text="文生图")

        ttk.Label(text_tab, text="Prompt").grid(row=0, column=0, sticky="w")
        text_prompt_frame = ttk.Frame(text_tab)
        text_prompt_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 10))
        text_prompt_frame.columnconfigure(0, weight=1)
        text_prompt_frame.rowconfigure(0, weight=1)
        self.text_prompt = tk.Text(text_prompt_frame, height=9, wrap="word", undo=True)
        self.text_prompt.grid(row=0, column=0, sticky="nsew")
        text_prompt_scrollbar = ttk.Scrollbar(text_prompt_frame, command=self.text_prompt.yview)
        text_prompt_scrollbar.grid(row=0, column=1, sticky="ns")
        self.text_prompt.configure(yscrollcommand=text_prompt_scrollbar.set)
        self.text_prompt.insert(
            "1.0",
            "一只橘猫戴着橙色围巾抱着水獭，温暖插画风格，清晰细节，横向构图",
        )
        gen_btn = ttk.Button(text_tab, text="生成图片", command=self.start_generation)
        gen_btn.grid(row=2, column=0, sticky="e")
        self.buttons.append(gen_btn)

        edit_tab = ttk.Frame(tabs, padding=10)
        edit_tab.columnconfigure(1, weight=1)
        edit_tab.rowconfigure(5, weight=1)
        tabs.add(edit_tab, text="图片编辑 / 图生图")

        ttk.Label(edit_tab, text="参考图片").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        image_frame = ttk.Frame(edit_tab)
        image_frame.grid(row=0, column=1, sticky="ew")
        image_frame.columnconfigure(0, weight=1)
        self.image_listbox = tk.Listbox(image_frame, height=4, selectmode="extended", exportselection=False)
        self.image_listbox.grid(row=0, column=0, sticky="ew")
        image_scrollbar = ttk.Scrollbar(image_frame, command=self.image_listbox.yview)
        image_scrollbar.grid(row=0, column=1, sticky="ns")
        self.image_listbox.configure(yscrollcommand=image_scrollbar.set)
        ttk.Label(image_frame, textvariable=self.image_count).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        image_buttons = ttk.Frame(edit_tab)
        image_buttons.grid(row=0, column=2, sticky="new", padx=(8, 0))
        ttk.Button(image_buttons, text="选择图片", command=self.choose_images).grid(row=0, column=0, sticky="ew")
        ttk.Button(image_buttons, text="追加图片", command=self.add_images).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(image_buttons, text="移除选中", command=self.remove_selected_images).grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(image_buttons, text="清空图片", command=self.clear_images).grid(row=3, column=0, sticky="ew", pady=(6, 0))

        ttk.Label(edit_tab, text="Mask").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(edit_tab, textvariable=self.mask_path).grid(row=2, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(edit_tab, text="选择Mask", command=self.choose_mask).grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=(8, 0))
        ttk.Button(edit_tab, text="清空Mask", command=lambda: self.mask_path.set("")).grid(row=3, column=2, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Label(edit_tab, text="Prompt").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        edit_prompt_frame = ttk.Frame(edit_tab)
        edit_prompt_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(6, 10))
        edit_prompt_frame.columnconfigure(0, weight=1)
        edit_prompt_frame.rowconfigure(0, weight=1)
        self.edit_prompt = tk.Text(edit_prompt_frame, height=7, wrap="word", undo=True)
        self.edit_prompt.grid(row=0, column=0, sticky="nsew")
        edit_prompt_scrollbar = ttk.Scrollbar(edit_prompt_frame, command=self.edit_prompt.yview)
        edit_prompt_scrollbar.grid(row=0, column=1, sticky="ns")
        self.edit_prompt.configure(yscrollcommand=edit_prompt_scrollbar.set)
        self.edit_prompt.insert(
            "1.0",
            "保留图片里的主体和整体质感，在右上角加一枚红色小印章，印章上写 DEMO",
        )
        edit_btn = ttk.Button(edit_tab, text="编辑图片", command=self.start_edit)
        edit_btn.grid(row=6, column=2, sticky="e")
        self.buttons.append(edit_btn)

        result_bar = ttk.Frame(root)
        result_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        result_bar.columnconfigure(1, weight=1)
        ttk.Label(result_bar, text="最近保存").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(result_bar, textvariable=self.last_file, state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Button(result_bar, text="打开目录", command=self.open_output_dir).grid(row=0, column=2, sticky="e", padx=(8, 0))

        log_frame = ttk.LabelFrame(root, text="日志", padding=8)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _combo(self, parent: ttk.Frame, label: str, key: str, values: list[str], row: int, column: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(0 if row == 0 else 8, 0))
        combo = ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly", width=14)
        combo.grid(row=row, column=column + 1, sticky="ew", padx=(0, 12), pady=(0 if row == 0 else 8, 0))

    def _entry(self, parent: ttk.Frame, label: str, key: str, row: int, column: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=(8, 0))
        ttk.Entry(parent, textvariable=self.vars[key], width=14).grid(row=row, column=column + 1, sticky="ew", padx=(0, 12), pady=(8, 0))

    def choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(resolve_output_dir(self.vars["output_dir"].get())))
        if folder:
            self.vars["output_dir"].set(folder)

    def choose_images(self) -> None:
        paths = filedialog.askopenfilenames(
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ]
        )
        if paths:
            self.set_image_paths(list(paths))

    def add_images(self) -> None:
        paths = filedialog.askopenfilenames(
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ]
        )
        if paths:
            self.set_image_paths([*self.image_paths, *paths])

    def remove_selected_images(self) -> None:
        if self.image_listbox is None:
            return
        selected = set(self.image_listbox.curselection())
        if not selected:
            return
        self.image_paths = [
            path
            for index, path in enumerate(self.image_paths)
            if index not in selected
        ]
        self.refresh_image_list()

    def clear_images(self) -> None:
        self.image_paths = []
        self.refresh_image_list()

    def set_image_paths(self, paths: list[str] | tuple[str, ...]) -> None:
        deduped: list[str] = []
        seen: set[str] = set()
        for raw_path in paths:
            path = str(raw_path).strip()
            if not path:
                continue
            key = normalize_path_key(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        self.image_paths = deduped
        self.refresh_image_list()

    def refresh_image_list(self) -> None:
        if self.image_listbox is not None:
            self.image_listbox.delete(0, "end")
            for path in self.image_paths:
                self.image_listbox.insert("end", path)

        count = len(self.image_paths)
        if count == 0:
            self.image_count.set("尚未选择图片")
        else:
            self.image_count.set(f"已选择 {count} 张参考图片")

    def choose_mask(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("PNG mask", "*.png"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.mask_path.set(path)

    def open_output_dir(self) -> None:
        output_dir = resolve_output_dir(self.vars["output_dir"].get())
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(output_dir)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("打开目录失败", str(exc))

    def save_config(self) -> None:
        config = self.collect_config()
        config["output_dir"] = safe_output_dir_value(config.get("output_dir", ""))
        try:
            CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("保存配置失败", str(exc))
            return
        self.log(f"配置已保存: {CONFIG_PATH}")

    def collect_config(self) -> dict[str, str]:
        return {key: var.get().strip() for key, var in self.vars.items()}

    def start_generation(self) -> None:
        if self.text_prompt is None:
            messagebox.showerror("界面未就绪", "文生图 Prompt 输入框还没有初始化。")
            return
        prompt = self.text_prompt.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("缺少 Prompt", "请先输入文生图 Prompt。")
            return
        self.start_worker("文生图", self.worker_generation, prompt)

    def start_edit(self) -> None:
        if self.edit_prompt is None:
            messagebox.showerror("界面未就绪", "图片编辑 Prompt 输入框还没有初始化。")
            return
        prompt = self.edit_prompt.get("1.0", "end").strip()
        image_paths = [path.strip() for path in self.image_paths if path.strip()]
        if not prompt:
            messagebox.showwarning("缺少 Prompt", "请先输入图片编辑 Prompt。")
            return
        if not image_paths:
            messagebox.showwarning("缺少图片", "请先选择至少一张本地参考图片。")
            return
        invalid_images = [path for path in image_paths if not Path(path).is_file()]
        if invalid_images:
            messagebox.showwarning("图片不存在", f"请选择有效的本地图片文件:\n{invalid_images[0]}")
            return
        mask_path = self.mask_path.get().strip()
        if mask_path and not Path(mask_path).is_file():
            messagebox.showwarning("Mask不存在", "请选择有效的 PNG mask，或清空 Mask。")
            return
        self.start_worker("图片编辑", self.worker_edit, prompt, image_paths, mask_path)

    def start_worker(self, task_name: str, target: Any, *args: Any) -> None:
        if requests is None:
            messagebox.showerror(
                "缺少依赖",
                "没有安装 requests。请先在当前目录运行: python -m pip install -r requirements.txt",
            )
            return
        config = self.collect_config()
        if not config["base_url"]:
            messagebox.showwarning("缺少 Base URL", "请输入 Base URL，例如 https://www.packyapi.com。")
            return
        if not config["api_key"]:
            messagebox.showwarning("缺少 API Key", "请输入 Bearer API Key。")
            return

        self.save_config()
        self.set_busy(True)
        self.log(f"{task_name}请求开始...")
        self.log(proxy_log_message(config))

        thread = threading.Thread(target=self._run_worker, args=(target, config, args), daemon=True)
        thread.start()

    def _run_worker(self, target: Any, config: dict[str, str], args: tuple[Any, ...]) -> None:
        try:
            saved_path = target(config, *args)
        except Exception as exc:  # noqa: BLE001 - report API and IO errors to the GUI
            self.events.put(("error", friendly_error_message(exc)))
        else:
            self.events.put(("done", saved_path))

    def worker_generation(self, config: dict[str, str], prompt: str) -> Path:
        url = build_endpoint(config["base_url"], "generations")
        payload: dict[str, Any] = {
            "model": config["model"] or "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": config["size"] or "auto",
            "quality": config["quality"] or "auto",
            "output_format": config["output_format"] or "png",
            "response_format": config["response_format"] or "url",
        }
        add_common_optional_fields(payload, config)

        self.events.put(("log", f"POST {url}"))
        session = build_session(config)
        response = session.post(
            url,
            headers=auth_headers(config["api_key"]),
            json=payload,
            timeout=600,
        )
        return self.handle_api_response(response, config)

    def worker_edit(self, config: dict[str, str], prompt: str, image_paths: list[str], mask_path: str) -> Path:
        url = build_endpoint(config["base_url"], "edits")
        data: dict[str, str] = {
            "model": config["model"] or "gpt-image-2",
            "prompt": prompt,
            "n": "1",
            "size": config["size"] or "auto",
            "quality": config["quality"] or "auto",
            "output_format": config["output_format"] or "png",
            "response_format": config["response_format"] or "url",
        }
        add_common_optional_fields(data, config)
        if config.get("input_fidelity"):
            data["input_fidelity"] = config["input_fidelity"]

        opened_files = []
        temp_files: list[Path] = []
        try:
            upload_image_paths, upload_mask_path, temp_files = prepare_edit_uploads(image_paths, mask_path, config)
            for index, (image_path, upload_image_path) in enumerate(zip(image_paths, upload_image_paths), start=1):
                label = "图片" if len(upload_image_paths) == 1 else f"图片{index}"
                self.events.put(("log", upload_summary(image_path, upload_image_path, label)))
            if mask_path and upload_mask_path:
                self.events.put(("log", upload_summary(mask_path, upload_mask_path, "Mask")))

            files: list[tuple[str, tuple[str, Any, str]]] = []
            image_field = "image" if len(upload_image_paths) == 1 else "image[]"
            for upload_image_path in upload_image_paths:
                image = open(upload_image_path, "rb")
                opened_files.append(image)
                files.append((
                    image_field,
                    (Path(upload_image_path).name, image, guess_mime(str(upload_image_path))),
                ))
            if upload_mask_path:
                mask = open(upload_mask_path, "rb")
                opened_files.append(mask)
                files.append(("mask", (Path(upload_mask_path).name, mask, "image/png")))

            self.events.put(("log", f"POST {url}"))
            session = build_session(config)
            response = session.post(
                url,
                headers=auth_headers(config["api_key"]),
                data=data,
                files=files,
                timeout=600,
            )
            return self.handle_api_response(response, config)
        finally:
            for file_obj in opened_files:
                file_obj.close()
            for temp_file in temp_files:
                try:
                    temp_file.unlink(missing_ok=True)
                except OSError:
                    pass

    def handle_api_response(self, response: Any, config: dict[str, str]) -> Path:
        text_preview = response.text[:800] if getattr(response, "text", None) else ""
        if response.status_code >= 400:
            raise RuntimeError(f"API请求失败: HTTP {response.status_code}\n{text_preview}")

        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeError(f"响应不是 JSON:\n{text_preview}") from exc

        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError(f"响应中没有 data[0]:\n{json.dumps(body, ensure_ascii=False, indent=2)[:1200]}")

        item = data[0]
        revised_prompt = item.get("revised_prompt")
        if revised_prompt:
            self.events.put(("log", f"revised_prompt: {revised_prompt}"))

        output_dir = resolve_output_dir(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        if item.get("url"):
            return download_image(item["url"], output_dir, config["output_format"], config)
        if item.get("b64_json"):
            return save_b64_image(item["b64_json"], output_dir, config["output_format"])

        raise RuntimeError(f"data[0] 中既没有 url 也没有 b64_json:\n{json.dumps(item, ensure_ascii=False, indent=2)[:1200]}")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self.buttons:
            button.configure(state=state)

    def _poll_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self.log(str(payload))
            elif event == "error":
                self.set_busy(False)
                self.log(f"失败: {payload}")
                messagebox.showerror("请求失败", str(payload))
            elif event == "done":
                self.set_busy(False)
                self.last_file.set(str(payload))
                self.log(f"图片已保存: {payload}")
                messagebox.showinfo("完成", f"图片已保存:\n{payload}")

        self.after(120, self._poll_events)

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def load_config() -> dict[str, str]:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            for key in config:
                if key in loaded and loaded[key] is not None:
                    config[key] = str(loaded[key])
    config["output_dir"] = safe_output_dir_value(config.get("output_dir", ""))
    return config


def safe_output_dir_value(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return DEFAULT_CONFIG["output_dir"]

    path = Path(text).expanduser()
    if not path.is_absolute():
        return text

    try:
        relative = path.resolve().relative_to(APP_DIR.resolve())
    except (OSError, ValueError):
        return DEFAULT_CONFIG["output_dir"]
    return str(relative) if str(relative) != "." else DEFAULT_CONFIG["output_dir"]


def resolve_output_dir(value: str) -> Path:
    text = (value or DEFAULT_CONFIG["output_dir"]).strip() or DEFAULT_CONFIG["output_dir"]
    path = Path(text).expanduser()
    if path.is_absolute():
        return path
    return APP_DIR / path


def build_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.strip().rstrip("/")
    if re.search(rf"/v1/images/{endpoint}/?$", base):
        return base
    if re.search(r"/v1/images/?$", base):
        return f"{base}/{endpoint}"
    if re.search(r"/v1/?$", base):
        return f"{base}/images/{endpoint}"
    return f"{base}/v1/images/{endpoint}"


def auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept": "*/*",
    }


def add_common_optional_fields(target: dict[str, Any], config: dict[str, str]) -> None:
    output_format = (config.get("output_format") or "").lower()
    compression = config.get("output_compression", "").strip()
    if output_format == "jpeg" and compression:
        try:
            target["output_compression"] = max(0, min(100, int(compression)))
        except ValueError:
            raise RuntimeError("JPEG压缩必须是 0 到 100 的整数。")

    if config.get("background"):
        target["background"] = config["background"]
    if config.get("moderation"):
        target["moderation"] = config["moderation"]


def build_session(config: dict[str, str]) -> Any:
    session = requests.Session()
    proxy_mode = config.get("proxy_mode", "不使用代理")

    if proxy_mode == "使用系统代理":
        session.trust_env = True
        return session

    session.trust_env = False
    if proxy_mode == "自定义代理":
        proxy_url = config.get("proxy_url", "").strip()
        if not proxy_url:
            raise RuntimeError("代理模式为“自定义代理”时，请填写代理地址，例如 http://127.0.0.1:7890。")
        session.proxies.update({
            "http": proxy_url,
            "https": proxy_url,
        })

    return session


def proxy_log_message(config: dict[str, str]) -> str:
    proxy_mode = config.get("proxy_mode", "不使用代理")
    if proxy_mode == "使用系统代理":
        return "代理模式: 使用系统代理"
    if proxy_mode == "自定义代理":
        proxy_url = config.get("proxy_url", "").strip() or "未填写"
        return f"代理模式: 自定义代理 {proxy_url}"
    return "代理模式: 不使用代理"


def prepare_edit_uploads(image_paths: list[str], mask_path: str, config: dict[str, str]) -> tuple[list[Path], Path | None, list[Path]]:
    source_images = [Path(path) for path in image_paths]
    source_mask = Path(mask_path) if mask_path else None

    if config.get("edit_preprocess", "开启") != "开启":
        return source_images, source_mask, []

    if Image is None:
        raise RuntimeError("编辑预处理需要 Pillow。请运行: python -m pip install -r requirements.txt")

    try:
        max_side = int(config.get("edit_max_side", "1024") or "1024")
    except ValueError as exc:
        raise RuntimeError("上传最长边必须是整数，例如 1024 或 1536。") from exc
    if max_side < 256:
        raise RuntimeError("上传最长边不能小于 256。")

    temp_files: list[Path] = []
    upload_images = [
        make_upload_copy(source_image, max_side, temp_files, prefer_png=False)
        for source_image in source_images
    ]
    upload_mask = make_upload_copy(source_mask, max_side, temp_files, prefer_png=True) if source_mask else None
    return upload_images, upload_mask, temp_files


def normalize_path_key(path: str) -> str:
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(Path(path)).casefold()


def make_upload_copy(source: Path | None, max_side: int, temp_files: list[Path], prefer_png: bool) -> Path | None:
    if source is None:
        return None

    with Image.open(source) as image:
        image.load()
        width, height = image.size
        longest = max(width, height)
        should_resize = longest > max_side
        suffix = ".png" if prefer_png or image.mode in {"RGBA", "LA", "P"} else ".jpg"

        if not should_resize and source.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            return source

        scale = min(1.0, max_side / longest)
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        if should_resize:
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        if suffix == ".jpg":
            image = image.convert("RGB")
        else:
            image = image.convert("RGBA")

        fd, temp_name = tempfile.mkstemp(prefix="image2_upload_", suffix=suffix)
        os.close(fd)
        temp = Path(temp_name)
        temp_files.append(temp)
        if suffix == ".jpg":
            image.save(temp, quality=90, optimize=True)
        else:
            image.save(temp, optimize=True)
        return temp


def image_info(path: Path) -> tuple[int, int, int]:
    size_bytes = path.stat().st_size
    if Image is None:
        return 0, 0, size_bytes
    with Image.open(path) as image:
        return image.width, image.height, size_bytes


def upload_summary(original_path: str, upload_path: Path, label: str) -> str:
    original = Path(original_path)
    original_w, original_h, original_bytes = image_info(original)
    upload_w, upload_h, upload_bytes = image_info(upload_path)
    original_size = format_bytes(original_bytes)
    upload_size = format_bytes(upload_bytes)
    if original.resolve() == upload_path.resolve():
        return f"{label}上传: {original.name} {original_w}x{original_h}, {original_size}"
    return (
        f"{label}上传副本: {original.name} {original_w}x{original_h}, {original_size} -> "
        f"{upload_path.name} {upload_w}x{upload_h}, {upload_size}"
    )


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{size}B"


def friendly_error_message(exc: Exception) -> str:
    message = str(exc)
    if "RemoteDisconnected" in message or "Remote end closed connection without response" in message:
        return (
            f"{message}\n\n"
            "服务器在生成结果前主动断开连接。常见原因是图片编辑耗时过长、上传图片过大、"
            "或上游网关约 60 秒超时。\n"
            "建议先这样重试：编辑预处理=开启，上传最长边=1024，质量=medium，尺寸=1024x1024。"
        )
    if "ProxyError" in message or "Unable to connect to proxy" in message:
        return (
            f"{message}\n\n"
            "这是代理连接问题。可以把代理模式改为“不使用代理”，或填写可用的自定义代理地址。"
        )
    return message


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def download_image(url: str, output_dir: Path, requested_format: str, config: dict[str, str]) -> Path:
    session = build_session(config)
    with session.get(url, timeout=600, stream=True) as response:
        if response.status_code >= 400:
            raise RuntimeError(f"图片下载失败: HTTP {response.status_code}\n{response.text[:500]}")

        ext = extension_from_content_type(response.headers.get("content-type", ""), requested_format)
        path = unique_output_path(output_dir, ext)
        with path.open("wb") as file_obj:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    file_obj.write(chunk)
    return path


def save_b64_image(b64_json: str, output_dir: Path, requested_format: str) -> Path:
    raw = b64_json.split(",", 1)[1] if b64_json.startswith("data:") and "," in b64_json else b64_json
    image_bytes = base64.b64decode(raw)
    ext = normalize_extension(requested_format)
    path = unique_output_path(output_dir, ext)
    path.write_bytes(image_bytes)
    return path


def extension_from_content_type(content_type: str, requested_format: str) -> str:
    content_type = content_type.lower().split(";", 1)[0].strip()
    if content_type == "image/png":
        return "png"
    if content_type in {"image/jpeg", "image/jpg"}:
        return "jpg"
    if content_type == "image/webp":
        return "webp"
    return normalize_extension(requested_format)


def normalize_extension(output_format: str) -> str:
    value = (output_format or "png").lower().strip(".")
    if value == "jpeg":
        return "jpg"
    if value in {"png", "jpg", "webp"}:
        return value
    return "png"


def unique_output_path(output_dir: Path, ext: str) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"image2_{timestamp}.{ext}"
    counter = 1
    while path.exists():
        path = output_dir / f"image2_{timestamp}_{counter}.{ext}"
        counter += 1
    return path


def main() -> None:
    app = Image2Gui()
    app.mainloop()


if __name__ == "__main__":
    main()
