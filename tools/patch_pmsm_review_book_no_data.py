"""将已生成的人可读校对册中的机器确认无数据单元格显示为“—”。

该工具只做小范围 OOXML 文本替换，不重新生成整本校对册，也不改变机器
JSON 的 ``null`` 语义。它用于在标准包追加人工确认后，把已有交付副本与
校对册生成器的显示规则同步，避免为三处单元格重复构建五万余行工作簿。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


TARGETS = {
    # “标准数据平铺”是第三个工作表；行号由同源机器包路径稳定生成。
    "H11686": "—",
    "J11686": "—",
    "H11693": "—",
    "J11693": "—",
    "H11700": "—",
    "J11700": "—",
}


def patch(path: Path) -> int:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    changed = 0
    try:
        with ZipFile(path, "r") as source, ZipFile(temp, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                payload = source.read(info.filename)
                if info.filename == "xl/worksheets/sheet3.xml":
                    text = payload.decode("utf-8")
                    for ref, value in TARGETS.items():
                        before = f'<c r="{ref}" t="inlineStr"></c>'
                        after = f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
                        if before in text:
                            text = text.replace(before, after, 1)
                            changed += 1
                        elif after in text:
                            # 已经同步过时保持幂等，便于交付前重复执行检查。
                            changed += 1
                    payload = text.encode("utf-8")
                target.writestr(info, payload)
        if changed != len(TARGETS):
            raise ValueError(f"预期修改{len(TARGETS)}个单元格，实际修改{changed}个")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="同步PMSM人工校对册无数据显示")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(f"已修改{patch(args.path)}个单元格: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
