"""从已保存的批次快照展示设备台数，不重算评价或用行数代替台数。"""

from collections.abc import Mapping


def format_device_summary_lines(sheets) -> list[str]:
    lines: list[str] = []
    for sheet in sheets or ():
        if not isinstance(sheet, Mapping) or not sheet.get("data_row_count"):
            continue
        name = str(sheet.get("sheet_name") or "设备")
        total = sheet.get("total_quantity")
        quantity = f"共 {total} 台" if total is not None else "总台数未记录"
        lines.append(f"{name}：{quantity}（数据 {sheet['data_row_count']} 行）")
        distribution = sheet.get("conclusion_quantities")
        if isinstance(distribution, Mapping):
            labels = ("1级", "2级", "3级", "未达3级", "不在范围", "无法判定")
            if any(label not in labels for label in distribution):
                labels = tuple(distribution)
            parts = [f"{label} {distribution.get(label, 0)} 台" for label in labels]
            # 旧快照可能使用旧结论文案；原样保留，不重新解释历史结果。
            lines.append("；".join(parts))
        else:
            lines.append("各等级台数未记录")
        if sheet.get("input_error_rows"):
            lines.append(
                f"输入错误 {sheet['input_error_rows']} 行"
                f"（已知数量 {sheet.get('input_error_quantity', 0)} 台；数量无效的行未计入台数）")
        if sheet.get("execution_error_rows"):
            lines.append(f"执行失败 {sheet['execution_error_rows']} 行，未计入等级分布")
    return lines
