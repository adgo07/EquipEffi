# -*- coding: utf-8 -*-
"""devices/base.py - 判定器基类与公共工具"""
import math
import json
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # 打包运行：优先exe同目录standards/（升级换数据），否则用内置
    _ext = Path(sys.executable).parent / "standards"
    STD_DIR = _ext if _ext.exists() else Path(getattr(sys, "_MEIPASS", ".")) / "standards"
else:
    STD_DIR = Path(__file__).resolve().parent.parent / "standards"

# 结果常量
LEVEL_1 = "1级"
LEVEL_2 = "2级"
LEVEL_3 = "3级"
NOT_MEET_3 = "未达3级"
CANNOT_JUDGE = "无法判定"
NOT_IN_RANGE = "不在范围"
PASS = "达标"
NOT_PASS = "未达标"
ENERGY_SAVING = "节能评价值"


def load_standard(key: str) -> dict:
    return json.loads((STD_DIR / f"{key}.json").read_text(encoding="utf-8"))


def to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("kW", "").replace("kw", "").replace("Ｗ", "").replace("，", ".")
    s = s.replace(",", "").replace(" ", "").replace("／", "").replace("/", "").replace("—", "")
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def interp(x, x1, x2, y1, y2):
    """线性插值；x1==x2时返回y1"""
    if x1 is None or x2 is None or y1 is None or y2 is None:
        return None
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


def find_bracket(sorted_vals, x):
    """在升序列表中找x的档位区间，返回(下档值, 上档值)。
    等于某档→(该档, 该档)；小于最小→(None, 最小)；大于最大→(最大, None)"""
    if not sorted_vals:
        return None, None
    if x <= sorted_vals[0]:
        return sorted_vals[0], sorted_vals[0] if x == sorted_vals[0] else None
    if x >= sorted_vals[-1]:
        return sorted_vals[-1], sorted_vals[-1] if x == sorted_vals[-1] else None
    for i in range(len(sorted_vals) - 1):
        lo, hi = sorted_vals[i], sorted_vals[i + 1]
        if lo <= x <= hi:
            return lo, hi
    return None, None


def match_rows(rows, **filters):
    """按条件过滤行列表（None/空值条件忽略）"""
    out = rows
    for k, v in filters.items():
        if v in (None, ""):
            continue
        out = [r for r in out if str(r.get(k, "")).strip() == str(v).strip()]
    return out


def pick_best(rows, prefer):
    """从候选行中按偏好选最优（偏好列表：字段名→值，先精确后忽略）"""
    for key, val in prefer:
        if val in (None, ""):
            continue
        hit = [r for r in rows if str(r.get(key, "")).strip() == str(val).strip()]
        if hit:
            return hit
    return rows


class BaseEvaluator:
    """判定器基类。子类实现 evaluate(params) -> dict
    返回字段：
      level1/level2/level3: 各级限值（或None）
      result: 判定结论
      basis: 判定依据（标准+条款）
      note: 备注/警告
      review: 是否需人工复核
    """

    code = ""
    name = ""
    standard_key = ""

    def __init__(self):
        self.standard = load_standard(self.standard_key) if self.standard_key else {}

    def evaluate(self, params: dict) -> dict:
        raise NotImplementedError

    def result(self, l1, l2, l3, actual, better_smaller=False, compare=None):
        """通用限值比较判定。
        better_smaller=True: 实际≤限值越好（比功率/损耗/单耗类）
        compare: 自定义比较函数(actual, limit)->bool（达标）
        """
        if actual is None:
            return {"result": CANNOT_JUDGE, "note": "缺少实测值"}
        if l1 is not None and self._meet(actual, l1, better_smaller, compare):
            return {"result": LEVEL_1}
        if l2 is not None and self._meet(actual, l2, better_smaller, compare):
            return {"result": LEVEL_2}
        if l3 is not None and self._meet(actual, l3, better_smaller, compare):
            return {"result": LEVEL_3}
        return {"result": NOT_MEET_3}

    @staticmethod
    def _meet(actual, limit, better_smaller, compare):
        if compare:
            return compare(actual, limit)
        return actual <= limit if better_smaller else actual >= limit
