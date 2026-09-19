"""Presentation-side projection helpers for the unified field metadata.

The domain registry stores canonical field IDs and their optional V4 mapping.
This module only checks/projections presentation payloads; it does not read
Excel files, open Tk, normalize input, or perform an efficiency evaluation.
It is intentionally usable by API, desktop, Web, and a future mobile adapter.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..domain.evaluation.metadata import DeviceProfile, get_device_profile


class MetadataProjectionError(ValueError):
    """A presentation contract cannot be reconciled with domain metadata."""


def metadata_fallback_input_payloads(
    public_device_type: str,
    existing_field_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Build fallback payloads for V4 inputs absent from legacy specs.

    Some public V4 sheets contain input columns that the older internal
    ``device_specs`` profile never modeled (for example ``duct_ac``'s
    ``enthalpy`` column).  The metadata registry is the authoritative bridge
    for these fields.  Only visible V4-mapped input fields not already present
    in the legacy fallback are returned, so this helper cannot duplicate or
    expose internal-only fields such as ``production_year``.
    """

    existing = {str(field_id) for field_id in existing_field_ids}
    # The fallback form is presentation-only, but its validation hint must be
    # identical to the dependency-free API schema.  Import lazily to keep the
    # domain metadata module usable without pulling in the application layer.
    from ..application.services.schema_constraints import fallback_field_metadata
    data_type_names = {
        "text": "文本",
        "number": "数值",
        "integer": "整数",
        "percentage": "数值",
        "image": "图片",
    }

    def bound(value: Any) -> int | float | None:
        if value is None:
            return None
        if hasattr(value, "to_integral_value"):
            return int(value) if value == value.to_integral_value() else float(value)
        return value

    profile = get_device_profile(public_device_type)
    payloads: list[dict[str, Any]] = []
    for field in profile.input_fields:
        # Attachments/notes are handled by the common fallback contract; this
        # helper is only for missing device-parameter columns.
        if field.group != "设备参数" or field.field_id in existing or not field.v4_field_id:
            continue
        fallback_metadata = fallback_field_metadata(public_device_type, field.field_id)
        validation = field.required_condition
        hint = str(fallback_metadata.get("validation", "") or "")
        if hint and hint not in validation:
            validation = f"{validation}；{hint}" if validation else hint
        payload = {
            "field_id": field.field_id,
            "display_name": field.display_name,
            "group": field.group,
            "data_type": data_type_names.get(field.data_type, "文本"),
            "unit": field.unit,
            "editable": field.editable,
            "required": "必填" if field.required else "可选",
            "validation": validation,
            "minimum": fallback_metadata.get("minimum", bound(field.minimum)),
            "maximum": fallback_metadata.get("maximum", bound(field.maximum)),
            "enum_name": field.enum_name,
            "enum_values": list(field.enum_values),
        }
        if fallback_metadata.get("conditional_limits"):
            payload["conditional_limits"] = fallback_metadata["conditional_limits"]
        payloads.append(payload)
    return payloads


def metadata_v4_field_map(profile: DeviceProfile) -> dict[str, Any]:
    """Return the profile's unambiguous canonical-to-V4 input map."""

    mapped: dict[str, Any] = {}
    for field in profile.input_fields:
        if not field.v4_field_id:
            # Internal-only fields (for example production_year) are not V4
            # form columns and must not be guessed into the visible contract.
            continue
        v4_id = str(field.v4_field_id)
        previous = mapped.get(v4_id)
        if previous is not None and previous.field_id != field.field_id:
            raise MetadataProjectionError(
                f"公共设备{profile.public_type}存在重复V4字段映射: {v4_id}"
            )
        mapped[v4_id] = field
    return mapped


def project_v4_input_payloads(
    profile: DeviceProfile,
    payloads: Iterable[dict[str, Any]],
    *,
    context: str = "V4",
) -> list[dict[str, Any]]:
    """Validate and copy V4 input payloads using one metadata profile.

    The payload shape and presentation values are preserved.  Metadata owns
    field identity, order, display-name/unit mapping and editability checks;
    the caller's V4 contract remains the source for exact validation strings,
    enum values and conditional limits.
    """

    profile_map = metadata_v4_field_map(profile)
    projected = [dict(item) for item in payloads]
    expected_ids = [
        str(field.v4_field_id)
        for field in profile.input_fields
        if field.v4_field_id
    ]
    actual_ids = [str(item.get("field_id", "")) for item in projected]
    if actual_ids != expected_ids:
        raise MetadataProjectionError(
            f"{context}字段顺序或覆盖范围与元数据不一致: "
            f"metadata={expected_ids!r}, contract={actual_ids!r}"
        )
    for item in projected:
        field_id = str(item.get("field_id", ""))
        field = profile_map.get(field_id)
        if field is None:
            raise MetadataProjectionError(
                f"{context}字段未在元数据中登记: {field_id}"
            )
        if field.v4_display_name != item.get("display_name"):
            raise MetadataProjectionError(
                f"{context}字段显示名称不一致: {field_id}"
            )
        if field.v4_unit != item.get("unit"):
            raise MetadataProjectionError(f"{context}字段单位不一致: {field_id}")
        # Desktop form payloads historically omitted this presentation key;
        # editable_only=True already guarantees it is an input.  API payloads
        # include the key, so accept the legacy omission as ``True``.
        if field.editable != bool(item.get("editable", True)):
            raise MetadataProjectionError(
                f"{context}字段可编辑状态不一致: {field_id}"
            )
    return projected


def validate_fallback_input_payloads(
    public_device_type: str,
    payloads: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check legacy fallback fields without changing their public shape/order."""

    profile = get_device_profile(public_device_type)
    by_id = {field.field_id: field for field in profile.input_fields}
    by_v4_id = metadata_v4_field_map(profile)
    checked = [dict(item) for item in payloads]
    for item in checked:
        field_id = str(item.get("field_id", ""))
        field = by_id.get(field_id) or by_v4_id.get(field_id)
        if field is None:
            raise MetadataProjectionError(
                f"公共设备{public_device_type}的回退schema字段未登记: {field_id}"
            )
        if not field.editable or field.role != "input":
            raise MetadataProjectionError(
                f"公共设备{public_device_type}的回退schema字段不是可编辑输入: {field_id}"
            )
    return checked


def project_input_payloads(
    public_device_type: str,
    payloads: Iterable[dict[str, Any]],
    *,
    mode: str,
    context: str = "字段",
) -> list[dict[str, Any]]:
    """Use one presentation projection entry point for both form modes.

    ``mode='v4'`` checks the exact V4 field order and presentation mapping;
    ``mode='fallback'`` checks legacy canonical/V4 IDs while preserving the
    fallback payload shape.  Keeping the dispatch here prevents API and
    desktop code from reimplementing profile lookup or alias handling.
    """

    profile = get_device_profile(public_device_type)
    if mode == "v4":
        return project_v4_input_payloads(profile, payloads, context=context)
    if mode == "fallback":
        return validate_fallback_input_payloads(public_device_type, payloads)
    raise MetadataProjectionError(f"未知字段投影模式: {mode}")


__all__ = [
    "MetadataProjectionError",
    "metadata_fallback_input_payloads",
    "metadata_v4_field_map",
    "project_input_payloads",
    "project_v4_input_payloads",
    "validate_fallback_input_payloads",
]
