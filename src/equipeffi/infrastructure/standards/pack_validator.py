from __future__ import annotations

import math
from typing import Any


class StandardPackValidator:
    """标准数据包的保守结构校验入口。

    该校验器不推断标准数值，也不根据趋势修正数据；它只拒绝会使查表
    结果不可追溯或不可计算的明显结构问题。不同设备包可以使用 ``rows``、
    ``records``、``tables`` 或嵌套 ``devices``，因此校验采用可组合规则。
    """

    _STATUSES = {"extracted", "normalized", "verified", "active"}
    # Standard packs intentionally use several shapes: pump keeps separate
    # ``water``/``chemical`` formula trees and heat-treatment keeps ``table8``
    # plus fuel coefficients.  All of these are data containers, not metadata.
    _DATA_KEYS = {
        "rows", "records", "tables", "devices", "sections", "water", "chemical",
        "table8", "fuel_coefficients", "product_standard_calculation",
    }

    def validate(self, pack: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(pack, dict):
            return ["标准数据包必须是对象"]

        status = pack.get("status")
        if status not in (None, "") and str(status) not in self._STATUSES:
            errors.append(f"status不是允许的数据状态: {status}")
        for key in ("standard_code", "standard_name"):
            if key in pack and pack[key] in (None, ""):
                errors.append(f"{key}不能为空")

        if not any(key in pack for key in self._DATA_KEYS):
            errors.append("标准数据包缺少rows、records、tables、devices或sections数据容器")

        self._walk(pack, "$", errors)
        # data_id is the join key used by the human-readable review book and
        # by evaluation traces.  It must therefore be unique across the
        # entire pack, not merely within each individual ``rows``/``tables``
        # list.  A global set catches accidental collisions introduced when
        # several standard tables are merged into one package.
        self._validate_collections(pack, "$", errors, set())
        # ``suspicious_cells`` 是人工复核门禁。即使有人手工把manifest或
        # JSON状态改成active，也不能让带存疑单元格的标准进入评价器。
        if str(status) == "active" and self._has_suspicious_cells(pack):
            errors.append("active标准数据包仍包含未复核的suspicious_cells")
        return errors

    def _has_suspicious_cells(self, value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("suspicious_cells"):
                return True
            return any(self._has_suspicious_cells(child) for child in value.values())
        if isinstance(value, list):
            return any(self._has_suspicious_cells(child) for child in value)
        return False

    @staticmethod
    def _flatten_scalars(value: Any) -> list[Any]:
        """按标准JSON中的数组顺序展开效率叶节点。"""
        if isinstance(value, list):
            result: list[Any] = []
            for child in value:
                result.extend(StandardPackValidator._flatten_scalars(child))
            return result
        if isinstance(value, dict):
            # 效率等级键通常为“1”“2”“3”；数字顺序比JSON插入顺序
            # 更稳定，也能覆盖人工编辑后键顺序变化的情况。
            keys = sorted(value, key=lambda item: (0, int(str(item))) if str(item).isdigit() else (1, str(item)))
            result = []
            for key in keys:
                result.extend(StandardPackValidator._flatten_scalars(value[key]))
            return result
        return [value]

    def _validate_no_data_table(self, table: Any, path: str, errors: list[str]) -> None:
        """校验表格行登记的无数据单元格，不把空值当作普通缺失。"""
        if not isinstance(table, dict):
            return
        dims = table.get("dims")
        for row_index, row in enumerate(table.get("rows", []) or []):
            if not isinstance(row, dict) or "no_data_cells" not in row:
                continue
            row_path = f"{path}.rows[{row_index}]"
            markers = row.get("no_data_cells")
            if not isinstance(markers, list):
                errors.append(f"{row_path}.no_data_cells必须是数组")
                continue
            if not isinstance(dims, list) or not dims:
                errors.append(f"{row_path}.no_data_cells所在表缺少dims")
            reason = row.get("no_data_reason")
            if reason in (None, ""):
                errors.append(f"{row_path}.no_data_cells缺少no_data_reason")
            leaves = self._flatten_scalars(row.get("efficiency"))
            suspicious = row.get("suspicious_cells", []) or []
            suspicious_set = {item for item in suspicious if isinstance(item, int) and not isinstance(item, bool)}
            seen: set[int] = set()
            for marker in markers:
                if isinstance(marker, bool) or not isinstance(marker, int):
                    errors.append(f"{row_path}.no_data_cells含非整数索引: {marker!r}")
                    continue
                if marker in seen:
                    errors.append(f"{row_path}.no_data_cells存在重复索引: {marker}")
                    continue
                seen.add(marker)
                if marker < 0 or marker >= len(leaves):
                    errors.append(f"{row_path}.no_data_cells索引越界: {marker}")
                    continue
                if leaves[marker] is not None:
                    errors.append(f"{row_path}.no_data_cells索引{marker}对应值必须为空")
                if marker in suspicious_set:
                    errors.append(f"{row_path}.no_data_cells与suspicious_cells重复: {marker}")

    def _walk(self, value: Any, path: str, errors: list[str]) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path}包含非有限数")
            return
        if isinstance(value, dict):
            for key, child in value.items():
                self._walk(child, f"{path}.{key}", errors)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._walk(child, f"{path}[{index}]", errors)

    def _validate_collections(
        self,
        value: Any,
        path: str,
        errors: list[str],
        seen_ids: set[str],
    ) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in {"rows", "records", "tables"}:
                    if not isinstance(child, list):
                        errors.append(f"{child_path}必须是数组")
                    else:
                        if key == "tables":
                            for table_index, table in enumerate(child):
                                self._validate_no_data_table(table, f"{child_path}[{table_index}]", errors)
                        ids: set[str] = set()
                        for index, row in enumerate(child):
                            row_path = f"{child_path}[{index}]"
                            if not isinstance(row, dict):
                                errors.append(f"{row_path}必须是对象")
                                continue
                            data_id = row.get("data_id")
                            if data_id not in (None, ""):
                                identifier = str(data_id)
                                if identifier in ids:
                                    errors.append(f"{child_path}存在重复data_id: {identifier}")
                                if identifier in seen_ids and identifier not in ids:
                                    errors.append(f"标准数据包存在重复data_id: {identifier}")
                                ids.add(identifier)
                                seen_ids.add(identifier)
                self._validate_collections(child, child_path, errors, seen_ids)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._validate_collections(child, f"{path}[{index}]", errors, seen_ids)
