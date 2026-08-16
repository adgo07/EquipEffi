"""
全局配置
"""
import os
import sys
from pathlib import Path

# 版本信息
APP_NAME = "设备能效分析软件"
APP_NAME_EN = "EquipEffi"
APP_VERSION = "0.1.0"
STANDARD_DATA_VERSION = "2026.08"

# 路径管理
def get_app_root():
    """获取应用根目录（开发环境=项目根，打包后=exe所在目录）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

APP_ROOT = get_app_root()
STANDARDS_DIR = APP_ROOT / "standards"

# 支持的设备类型（sheet名称 -> 设备判定器key）
DEVICE_SHEET_MAP = {
    "变压器": "transformer",
    "低压电动机": "motor_low_voltage",
    "高压电动机": "motor_high_voltage",
    "永磁同步电机": "motor_pmsm",
    "空压机": "compressor",
    "清水泵": "pump_centrifugal",
    "化工泵": "pump_centrifugal",  # 与清水泵共用标准
    "通风机": "fan_centrifugal",
    "鼓风机": "blower",
    "潜水电泵": "pump_submersible",
    "工业锅炉": "boiler",
    "热处理设备": "heat_treatment",
    "热泵和冷水机组": "chiller_heatpump",
    "热泵热水机": "heatpump_water",
    "风管送风式空调": "ac_ducted",
    "单元式空调": "ac_unitary",
    "多联式空调": "ac_vrf",
}

# 阶段1先实现的设备（王玮拍板：变压器+低压电机+清水泵+空压机）
PHASE1_DEVICES = {"transformer", "motor_low_voltage", "pump_centrifugal", "compressor"}

# 处理状态
STATUS_UNPROCESSED = "未处理"
STATUS_DONE = "已判定"
STATUS_REVIEW = "待复核"
STATUS_MANUAL = "人工修正"

# 能效等级颜色（ARGB）
LEVEL_COLORS = {
    "1级": "FFC6EFCE",      # 浅绿
    "2级": "FFBDD7EE",      # 浅蓝
    "3级": "FFFFF2CC",      # 浅黄
    "未达3级": "FFFFC7CE",  # 浅红
    "未辨识": "FFD9D9D9",   # 浅灰
    "无法判定": "FFD9D9D9", # 浅灰
    "不在范围": "FFD9D9D9", # 浅灰
    "淘汰": "FFFFC7CE",     # 浅红
}

# 异常行颜色
REVIEW_COLOR = "FFFFE699"  # 橙色标记待复核
