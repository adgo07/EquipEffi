# -*- coding: utf-8 -*-
"""main.py - 程序入口"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gui.main_window import run

if __name__ == "__main__":
    run()
