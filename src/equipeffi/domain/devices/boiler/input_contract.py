"""锅炉显式分类及19列共享输入契约；不从名称猜分类。"""
from dataclasses import dataclass

REVISION = "boiler-input.v1"
STANDARD_CODE = "GB 24500-2020"


@dataclass(frozen=True)
class Category:
    category_id: str
    label: str
    form: str | None
    heat: str | None
    basis: str = "LOWER"


HEATS = (("layer_coal", "层状燃煤"), ("fluid_coal", "流化床燃煤"),
         ("biomass", "生物质"), ("gas", "室燃天然气非冷凝"),
         ("gas_condensing_lower", "室燃天然气冷凝（低位效率）"),
         ("gas_condensing_higher", "室燃天然气冷凝（高位效率）"),
         ("oil", "室燃油"), ("chamber_coal", "室燃煤"), ("electric", "电加热"),
         ("mixed", "混烧／燃料不能唯一归类"))
CATEGORIES = tuple(Category(f"{form}_{heat}", f"固定式水介质{label}／{title}", form, heat,
                            "NOT_APPLICABLE" if heat == "electric" else "HIGHER" if heat == "gas_condensing_higher" else "LOWER")
                   for form, label in (("steam", "蒸汽锅炉"), ("hot_water", "热水锅炉"))
                   for heat, title in HEATS) + (
    Category("ORGANIC_HEAT_CARRIER", "有机热载体锅炉（未开放）", None, None),
    Category("OTHER_CATEGORY", "其他类别", None, None),
    Category("UNCERTAIN_CATEGORY", "不确定类别", None, None))
BY_ID = {c.category_id: c for c in CATEGORIES}
COALS = ("烟煤Ⅰ类", "烟煤Ⅱ类", "烟煤Ⅲ类", "贫煤", "无烟煤Ⅱ类", "无烟煤Ⅲ类", "褐煤")
FUEL_LABELS = {"biomass": "生物质", "gas": "天然气", "gas_condensing_lower": "天然气",
               "gas_condensing_higher": "天然气", "oil": "燃油", "chamber_coal": "煤", "electric": "电"}


@dataclass(frozen=True)
class Field:
    field_id: str
    label: str
    unit: str | None = None
    required: bool = False


class BoilerInputContract:
    categories = CATEGORIES
    contract_revision = REVISION

    def visible_fields(self, category, values=None):
        basic = tuple(Field(k, label) for k, label in (("device_name", "设备名称"),
                      ("model", "型号"), ("location", "安装位置"), ("user_note", "备注")))
        c = BY_ID.get(category)
        if c is None or c.form is None:
            return basic
        result = basic + (Field("rated_capacity", "额定蒸发量" if c.form == "steam" else "额定热功率",
                               "t/h" if c.form == "steam" else "MW",
                               c.heat != "mixed" and (c.form == "hot_water" or c.heat in {"layer_coal", "biomass"})),
                          Field("rated_pressure_mpa", "额定蒸汽压力" if c.form == "steam" else "额定出水压力", "MPa", c.heat != "mixed"))
        if c.heat == "mixed":
            return result
        result += (Field("fuel", "能源／燃料品种", required=True),)
        if c.heat in {"layer_coal", "fluid_coal", "biomass"}:
            result += (Field("qnet_kj_kg", "收到基低位发热量", "kJ/kg", True),)
        if c.heat in {"layer_coal", "fluid_coal"}:
            result += (Field("vdaf_pct", "干燥无灰基挥发分", "%", True),)
        result += (Field("efficiency_pct", "热效率", "%", True),)
        # Qt条件显示依据由同一精确输入规则提供；无值时先不展示设计输入。
        if is_low_biomass(category, (values or {}).get("qnet_kj_kg")):
            result += (Field("design_limit_pct", "设计热效率（三级下限）", "%", True),)
        return result

    def options(self, category, field_id):
        c = BY_ID.get(category)
        if field_id != "fuel" or c is None:
            return ()
        labels = COALS if c.heat in {"layer_coal", "fluid_coal"} else (FUEL_LABELS[c.heat],) if c.heat in FUEL_LABELS else ()
        return tuple((s, s) for s in labels)


def is_low_biomass(category, qnet):
    c = BY_ID.get(category)
    if c is None or c.heat != "biomass" or qnet in (None, ""):
        return False
    from .calculator import exact_decimal, PROFILE_ID
    try:
        return exact_decimal(qnet, numeric_profile_id=PROFILE_ID) < 8374
    except ValueError:
        return False


CONTRACT = BoilerInputContract()
