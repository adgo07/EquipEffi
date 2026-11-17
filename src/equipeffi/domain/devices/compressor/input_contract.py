"""GB19153候选输入：显式分类，不猜测功率口径。"""
from dataclasses import dataclass

REVISION = "compressor-input.v1"
STANDARD_CODE = "GB 19153-2019"


@dataclass(frozen=True)
class Category:
    category_id: str
    label: str
    table_no: int | None


@dataclass(frozen=True)
class Field:
    field_id: str
    label: str
    unit: str | None = None
    required: bool = False


CATEGORIES = tuple(Category(*row) for row in (
    ("oil_injected_rotary", "一般用喷油回转空气压缩机", 1),
    ("variable_speed_oil_injected_rotary", "一般用变转速喷油回转空气压缩机", 2),
    ("reciprocating", "一般用往复活塞空气压缩机", 3),
    ("oil_free_reciprocating", "全无油润滑往复活塞空气压缩机", 4),
    ("portable_lubricated", "直联便携式润滑往复活塞空气压缩机", 5),
    ("portable_oil_free", "直联便携式无油往复活塞空气压缩机", 6),
    ("OTHER_CATEGORY", "其他类别", None), ("UNCERTAIN_CATEGORY", "不确定类别", None)))


class CompressorInputContract:
    categories = CATEGORIES
    contract_revision = REVISION

    def visible_fields(self, category):
        item = next((x for x in CATEGORIES if x.category_id == category), None)
        basic = (
            Field(
                "device_name", "设备名称"), Field(
                "model", "型号"), Field(
                "location", "位置"), Field(
                    "user_note", "备注"))
        if item is None or item.table_no is None:
            return basic
        portable = item.table_no >= 5
        return basic + (Field("rated_input_power_kw" if portable else "rated_motor_output_power_kw",
                              "机组额定输入功率" if portable else "电动机额定输出功率（主驱动合计）" if item.table_no in (1, 2) else "电动机额定输出功率", "kW", True),
                        Field(
            "rated_discharge_pressure_mpa",
            "额定排气压力（表压）",
            "MPa",
            True),
            *((Field("cooling_method", "冷却方式", None, True),) if not portable else ()),
            Field(
            "specific_power_kw_per_m3_min",
            "有效综合比功率" if item.table_no == 2 else "有效机组比功率",
            "kW/(m³/min)",
            True),
            Field("volume_flow_m3_min", "容积流量", "m³/min"))

    def options(self, category, field_id):
        return (("AIR", "风冷"), ("LIQUID", "液冷")
                ) if field_id == "cooling_method" else ()

    def scope_hint(self, category):
        return ""


CONTRACT = CompressorInputContract()
