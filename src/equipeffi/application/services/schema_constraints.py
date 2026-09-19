"""公共接口回退字段的数值约束元数据。

V4工作簿可用时，字段的最小值、最大值和枚举来自 ``配置`` sheet。
当工作簿未随宿主部署或暂时不可读时，API/桌面仍需要给出与
``V4ValidationService``一致的即时提示。本模块只生成展示层元数据，
不执行清洗、标准查表或能效判定，也不会改写输入值。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, profiles_for_public_type
from ...domain.evaluation.metadata import get_device_profile
from .input_normalization import DEVICE_ALIASES
from .v4_template_contract import CONDITIONAL_LIMITS
from .v4_validation import (
    INTEGER_FIELDS,
    NON_NEGATIVE_FIELDS,
    PERCENT_FIELDS,
    POSITIVE_FIELDS,
    RANGE_FIELDS,
)


# Open-ended bounds that have been explicitly reviewed against V4.  Positive
# fields not listed here continue to use the legacy fallback hint until their
# own migration is approved.
_METADATA_OPEN_BOUND_FIELDS = frozenset({"rated_temperature_c", "machine_no", "cooling_capacity_w", "heating_capacity_w"})
# V4 distinguishes non-negative inputs from strict positive design values.
# Keep this separate so a lower-bound hint of0 does not change the validation
# text or reject a legitimate zero.
_METADATA_NON_NEGATIVE_OPEN_BOUND_FIELDS = frozenset({"external_static_pressure_pa"})


def _field_aliases(public_code: str, field_id: str) -> set[str]:
    """Return the canonical field and its V4/兼容 aliases."""

    aliases = {str(field_id)}
    for profile in profiles_for_public_type(public_code) or (public_code,):
        aliases.update(
            source
            for source, target in DEVICE_ALIASES.get(profile, {}).items()
            if target == field_id
        )
    return aliases


def _metadata_field(public_code: str, field_id: str):
    """Find a metadata field by canonical or V4 ID without widening fallback rules."""

    try:
        profile = get_device_profile(public_code)
    except (KeyError, ValueError):
        return None
    try:
        return profile.field(str(field_id))
    except KeyError:
        return next(
            (field for field in profile.input_fields if field.v4_field_id == str(field_id)),
            None,
        )


def _json_number(value: Any) -> Any:
    """Convert internal Decimal bounds to JSON/schema-friendly numbers."""

    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def fallback_field_metadata(public_code: str, field_id: str) -> dict[str, Any]:
    """Return conservative UI metadata for one fallback field.

    ``minimum``/``maximum`` intentionally mirror the V4 validation boundary
    representation: positive fields use a minimum of ``0`` because Excel and
    browser controls use the lower bound as an input hint while the service
    still enforces strict ``>0``. Integer counts use ``1``. A condition such
    as the condensing-boiler 110% upper bound is exposed separately through
    ``conditional_limits``; the generic maximum remains the safe superset.
    """

    sheet_name = PUBLIC_DEVICE_NAMES.get(public_code, public_code)
    aliases = _field_aliases(public_code, field_id)
    minimum: Any = None
    maximum: Any = None
    validation = ""

    if field_id == "quantity":
        minimum = 1
        validation = "正整数"

    # A range rule is more specific than a generic positive/non-negative rule.
    for candidate in aliases:
        bounds = RANGE_FIELDS.get(sheet_name, {}).get(candidate)
        if bounds is not None:
            minimum, maximum = bounds
            validation = f"{minimum}～{maximum}"
            break

    if minimum is None and any(candidate in INTEGER_FIELDS.get(sheet_name, ()) for candidate in aliases):
        minimum = 1
        validation = "正整数"

    if minimum is None and any(candidate in POSITIVE_FIELDS.get(sheet_name, ()) for candidate in aliases):
        # Match the V4 contract's input hint (数值>0) while leaving the strict
        # rejection of zero to the validation/evaluation layer.
        minimum = 0
        validation = "数值>0"

    if minimum is None and any(candidate in NON_NEGATIVE_FIELDS.get(sheet_name, ()) for candidate in aliases):
        minimum = 0
        validation = "数值≥0"

    if any(candidate in PERCENT_FIELDS for candidate in aliases):
        minimum, maximum = 1, 100
        validation = "百分数本值1～100"

    # GB 24500-2020 allows a condensing gas boiler's design efficiency to
    # reach 110%; the normal (non-condensing) branch is narrowed dynamically
    # by the conditional rule below.
    if sheet_name == "工业锅炉" and field_id == "design_efficiency":
        minimum, maximum = 1, 110
        validation = "非冷凝1～100；冷凝1～110"

    # Numeric bounds already verified against the V4 contract should also drive
    # the dependency-free fallback schema.  Finite ranges replace both bounds;
    # open-ended integer lower bounds (currently ``级数``) replace only the
    # lower-bound hint.  Other open-ended positive hints and legacy aliases
    # keep their established representation until their own migration is
    # reviewed.
    metadata_field = _metadata_field(public_code, field_id)
    if (
        metadata_field is not None
        and metadata_field.data_type in {"number", "integer"}
        and metadata_field.minimum is not None
        and (
            metadata_field.maximum is not None
            or metadata_field.data_type == "integer"
            or metadata_field.field_id in _METADATA_OPEN_BOUND_FIELDS
            or metadata_field.field_id in _METADATA_NON_NEGATIVE_OPEN_BOUND_FIELDS
        )
    ):
        minimum = _json_number(metadata_field.minimum)
        if metadata_field.maximum is not None:
            maximum = _json_number(metadata_field.maximum)
            validation = f"{minimum}～{maximum}"
        elif metadata_field.data_type == "integer" and minimum == 1:
            validation = "正整数"
        elif metadata_field.field_id in _METADATA_NON_NEGATIVE_OPEN_BOUND_FIELDS and minimum == 0:
            validation = "数值≥0"
        elif metadata_field.field_id in _METADATA_OPEN_BOUND_FIELDS and minimum == 0:
            # V4 uses 0 as the UI lower-bound hint but validates strictly
            # greater than zero for this open-ended design temperature.
            validation = "数值>0"
        else:
            validation = f"数值≥{minimum}"

    metadata: dict[str, Any] = {
        "minimum": _json_number(minimum),
        "maximum": _json_number(maximum),
        "validation": validation,
    }
    conditional = CONDITIONAL_LIMITS.get((sheet_name, str(field_id)))
    if conditional:
        metadata["conditional_limits"] = [dict(rule) for rule in conditional]
    return metadata
