from enum import StrEnum


class DataStatus(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"


class StandardDataStatus(StrEnum):
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    VERIFIED = "verified"
    ACTIVE = "active"


class Conclusion(StrEnum):
    OUT_OF_SCOPE = "不在范围"
    NOT_APPLICABLE = "不适用"
    NOT_IN_RELEASE_SCOPE = "当前版本未支持"
    UNABLE_TO_JUDGE = "无法判定"
    ELIMINATED = "淘汰"
    NOT_COMPLIANT = "未达标"
    LEVEL_1 = "1级"
    LEVEL_2 = "2级"
    LEVEL_3 = "3级"
    LEVEL_4 = "4级"
    LEVEL_5 = "5级"
    SAVING_VALUE = "节能评价值"
    LIMIT_VALUE = "能效限定值"
    FIRST_CLASS = "一等"
    SECOND_CLASS = "二等"
    THIRD_CLASS = "三等"


class EliminationScope(StrEnum):
    INDUSTRY_ONLY = "仅产业结构调整指导目录"
    MOTOR_BATCHES_1_4 = "高耗能落后机电设备淘汰目录第一至第四批"
    INDUSTRY_AND_MOTOR_BATCHES = "产业结构调整指导目录+高耗能落后机电设备淘汰目录第一至第四批"


class ComparisonDirection(StrEnum):
    GREATER_OR_EQUAL = ">="
    LESS_OR_EQUAL = "<="


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
