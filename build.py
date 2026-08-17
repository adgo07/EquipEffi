# -*- coding: utf-8 -*-
"""build.py - 打包脚本（PyInstaller onefile）
用法: python build.py
产物: dist/设备能效分析工具.exe
说明: standards/ 数据目录会随exe分发（同目录），更新标准只换数据文件
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 收集standards下的JSON
std_files = [str(p) for p in (ROOT / "standards").glob("*.json")]
add_data = []
for f in std_files:
    add_data.append(f"{f};standards")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile", "--windowed",
    "--name", "设备能效分析工具",
]
icon = ROOT / "assets" / "app.ico"
if icon.exists():
    cmd += ["--icon", str(icon)]
for ad in add_data:
    cmd += ["--add-data", ad]
cmd += [str(ROOT / "main.py")]

print("运行:", " ".join(cmd))
subprocess.run(cmd, cwd=str(ROOT), check=True)
print("\n✅ 打包完成: dist/设备能效分析工具.exe")
print("分发时：exe + standards/ 目录放一起")
