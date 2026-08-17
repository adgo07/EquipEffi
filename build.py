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

# 用干净构建环境（避免hermes主环境numpy元数据问题）
PY = ROOT / ".venv_build" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)

# 收集standards下的JSON + 模板文件
std_files = [str(p) for p in (ROOT / "standards").glob("*.json")]
add_data = []
for f in std_files:
    add_data.append(f"{f};standards")
tpl = ROOT / "template" / "设备能效分析模板.xlsx"
if tpl.exists():
    add_data.append(f"{tpl};template")

cmd = [
    str(PY), "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile", "--windowed",
    "--name", "设备能效分析工具",
    "--exclude-module", "numpy", "--exclude-module", "pandas",
    "--collect-data", "tkinterdnd2",
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
