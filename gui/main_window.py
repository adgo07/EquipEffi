# -*- coding: utf-8 -*-
"""gui/main_window.py - 主窗口（tkinter，大众主流蓝白配色）
流程：选择输入Excel → 开始分析（后台线程）→ 清洗/判定/汇总 → 写回结果 → 完成
"""
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.cleaner import Cleaner
from core.evaluator import evaluate_all
from core.summary import build_summary

# ===== 大众主流配色（Windows 11 / Office风格）=====
COLOR_BG = "#F3F3F3"        # 窗口浅灰
COLOR_CARD = "#FFFFFF"      # 白色卡片
COLOR_PRIMARY = "#0078D4"   # 微软蓝（主按钮/标题）
COLOR_TEXT = "#333333"      # 正文深灰
COLOR_SUB = "#666666"       # 次级文字
COLOR_BORDER = "#E1E1E1"    # 边框
COLOR_OK = "#107C10"        # 成功绿
COLOR_WARN = "#D13438"      # 警示红
FONT = "Microsoft YaHei"


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.queue = queue.Queue()
        self.out_path = None
        root.title("设备能效分析工具")
        root.geometry("720x560")
        root.minsize(640, 500)
        root.configure(bg=COLOR_BG)
        self._build_ui()
        self._check_queue()

    # ---------- 界面 ----------
    def _build_ui(self):
        # 标题栏
        header = tk.Frame(self.root, bg=COLOR_PRIMARY, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="设备能效分析工具", bg=COLOR_PRIMARY, fg="white",
                 font=(FONT, 16, "bold")).pack(side="left", padx=24, pady=12)
        tk.Label(header, text="v0.1.0", bg=COLOR_PRIMARY, fg="#D0E8FF",
                 font=(FONT, 9)).pack(side="right", padx=24)

        # 内容区
        body = tk.Frame(self.root, bg=COLOR_BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # 输入文件卡片
        self._card = self._make_card(body)
        tk.Label(self._card, text="① 选择设备台账Excel", bg=COLOR_CARD, fg=COLOR_TEXT,
                 font=(FONT, 11, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 8))
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(self._card, textvariable=self.input_var, font=(FONT, 10))
        self.input_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.input_entry.insert(0, "请选择企业填写的设备台账文件…")
        self.input_entry.bind("<Button-1>", lambda e: self._browse_input())
        btn_style = {"font": (FONT, 10), "bg": "#E8F1FA", "fg": COLOR_PRIMARY,
                     "activebackground": "#D6E8F7", "relief": "flat", "cursor": "hand2"}
        tk.Button(self._card, text="浏览…", command=self._browse_input, **btn_style).grid(row=1, column=1)
        self._card.columnconfigure(0, weight=1)

        # 输出提示
        self.out_label = tk.Label(body, text="输出：与输入文件同目录，文件名加“_能效分析结果”",
                                  bg=COLOR_BG, fg=COLOR_SUB, font=(FONT, 9))
        self.out_label.pack(fill="x", pady=(6, 2))

        # 开始按钮
        self.start_btn = tk.Button(body, text="开始分析", command=self._start,
                                   bg=COLOR_PRIMARY, fg="white", font=(FONT, 12, "bold"),
                                   relief="flat", cursor="hand2", height=2,
                                   activebackground="#005A9E", activeforeground="white")
        self.start_btn.pack(fill="x", pady=10)

        # 进度条
        self.progress = ttk.Progressbar(body, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(4, 2))

        # 日志区
        log_frame = tk.Frame(body, bg=COLOR_BG)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=12, font=(FONT, 9), fg=COLOR_TEXT,
                           bg="white", relief="flat", wrap="word", state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)

        self._log("欢迎使用设备能效分析工具\n请选择企业填写的设备台账Excel文件，点击“开始分析”。")

    def _make_card(self, parent):
        card = tk.Frame(parent, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)
        inner = tk.Frame(card, bg=COLOR_CARD)
        inner.pack(fill="x", padx=14, pady=12)
        return inner

    # ---------- 交互 ----------
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="选择设备台账Excel",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")])
        if path:
            self.input_var.set(path)
            self._log(f"已选择：{path}")

    def _start(self):
        src = self.input_var.get().strip()
        if not src or not Path(src).exists():
            messagebox.showwarning("提示", "请先选择有效的Excel文件")
            return
        self.start_btn.configure(state="disabled", text="分析中…")
        self.progress["value"] = 0
        threading.Thread(target=self._worker, args=(src,), daemon=True).start()

    def _worker(self, src):
        """后台分析线程"""
        try:
            self._log("\n[1/4] 正在读取与清洗数据…")
            cleaner = Cleaner(src)
            devices = cleaner.run()
            n = sum(len(v) for v in devices.values())
            self._post("progress", 30)
            self._log(f"清洗完成：{len(devices)}类设备，共{n}台")

            self._log("[2/4] 正在判定能效等级…")
            results = evaluate_all(devices)
            self._post("progress", 65)
            judged = sum(1 for v in results.values() for it in v
                         if it["result_dict"]["result"] not in ("无法判定", "不在范围"))
            self._log(f"判定完成：{judged}台已判定")

            self._log("[3/4] 正在汇总统计…")
            summary = build_summary(results)
            self._post("progress", 80)
            for k, v in summary["total"].items():
                self._log(f"  {k}: {v}台")

            self._log("[4/4] 正在写回结果…")
            out = self._write_back(src, results)
            self._post("progress", 100)
            self._log(f"\n✅ 分析完成！\n输出文件：{out}")
            self._post("done", out)
        except Exception as e:
            self._post("error", f"分析失败：{type(e).__name__}: {e}")

    def _write_back(self, src, results):
        """写回判定结果到输出文件（zip补丁，图片保留）"""
        from core.writer import patch_cells
        src_path = Path(src)
        out = src_path.parent / f"{src_path.stem}_能效分析结果.xlsx"
        changes = {}
        for key, items in results.items():
            # 定位判定列（由清洗时的表头信息，此处用结果中的row）
            for it in items:
                sheet_name = self._sheet_name_for(key, src_path)
                if sheet_name is None:
                    continue
                col = self._judge_col(sheet_name, src_path)
                if col is None:
                    continue
                cell_ref = f"{col}{it['row']}"
                changes.setdefault(sheet_name, {})[cell_ref] = it["result_dict"]["result"]
        if not changes:
            # 无任何可写回 → 直接复制
            import shutil
            shutil.copy2(src, out)
        else:
            patch_cells(src, out, changes)
        return out

    def _sheet_name_for(self, key, src_path):
        """设备key → 输入文件中的sheet名（按SHEET_CONFIG反向）"""
        from core.cleaner import SHEET_CONFIG
        import openpyxl
        try:
            wb = openpyxl.load_workbook(src_path, read_only=True)
            names = wb.sheetnames
            wb.close()
        except Exception:
            return None
        for name, (k, _) in SHEET_CONFIG.items():
            if k == key and name in names:
                return name
        return None

    def _judge_col(self, sheet_name, src_path):
        """找sheet的能效判定列（表头含'能效判定'或'能效等级'或'能效'）"""
        import openpyxl
        wb = openpyxl.load_workbook(src_path, read_only=True)
        ws = wb[sheet_name]
        col = None
        for r in range(1, 6):
            for c in range(1, min(ws.max_column, 40) + 1):
                v = ws.cell(r, c).value
                if v and ("能效判定" in str(v) or "能效等级" in str(v) or "判定" in str(v)):
                    col = openpyxl.utils.get_column_letter(c)
                    break
            if col:
                break
        wb.close()
        return col

    # ---------- 队列/日志 ----------
    def _post(self, kind, data):
        self.queue.put((kind, data))

    def _check_queue(self):
        try:
            while True:
                kind, data = self.queue.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "progress":
                    self.progress["value"] = data
                elif kind == "done":
                    self.start_btn.configure(state="normal", text="开始分析")
                    if messagebox.askyesno("完成", f"分析完成！\n输出：{data}\n\n是否现在打开输出文件？"):
                        os.startfile(data)  # noqa: S606
                elif kind == "error":
                    self.start_btn.configure(state="normal", text="开始分析")
                    messagebox.showerror("错误", data)
        except queue.Empty:
            pass
        self.root.after(200, self._check_queue)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def run():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    run()
