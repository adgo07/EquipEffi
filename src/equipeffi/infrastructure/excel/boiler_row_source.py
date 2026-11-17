"""S列最小来源标记；仅供O条件输入辨识，不决定任何业务限值。"""
from hashlib import sha256
import json

MARKER = "EQUIPEFFI_BOILER_ROW_V1:"
CONTEXT_KEYS = ("device_name", "model", "location", "efficiency_pct", "category_id", "fuel", "rated_capacity", "rated_pressure_mpa", "qnet_kj_kg", "vdaf_pct")


def context(values):
    return {k: str(values.get(k) or "") for k in CONTEXT_KEYS}


def encode_source(source):
    text = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return MARKER + json.dumps({"facts": source, "sha256": sha256(text.encode()).hexdigest()}, ensure_ascii=False, separators=(",", ":"))


def decode_source(note):
    if MARKER not in str(note):
        return None
    try:
        item = json.loads(str(note).split(MARKER, 1)[1])
        text = json.dumps(item["facts"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if item["sha256"] != sha256(text.encode()).hexdigest():
            return None
        return item["facts"]
    except (TypeError, ValueError, KeyError):
        return None


def resolve_design_input(values, raw_o, note, *, has_outputs, is_result_workbook):
    """返回原词法设计值及来源状态；不拿普通输出充当输入。"""
    previous = decode_source(note)
    if previous is not None:
        same = previous.get("context") == context(values)
        if same and previous.get("o_kind") == "DESIGN_INPUT" and str(raw_o) == previous.get("o_output"):
            return previous.get("design_input", ""), "DESIGN_INPUT"
        # 明确改变O表示补录；不接受与旧输出相同的残留值。
        if str(raw_o) != previous.get("o_output") and raw_o not in (None, ""):
            return raw_o, "DESIGN_INPUT"
        return "", "SOURCE_AMBIGUOUS"
    if has_outputs or is_result_workbook or MARKER in str(note):
        return "", "SOURCE_AMBIGUOUS"
    return raw_o, "DESIGN_INPUT"
