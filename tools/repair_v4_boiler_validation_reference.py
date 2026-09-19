"""修复V4工业锅炉热效率验证公式的类别列引用。

模板的“设备类别”位于E列，“安装位置”位于F列。该工具只替换工业锅炉
工作表中的一段数据验证公式，不重建工作簿，避免破坏原有保护、表格和图片。
调用时显式提供输入和输出路径；输入文件不会被覆盖。
"""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile


OLD_FORMULA = (
    'OR(L4="",AND(ISNUMBER(L4),L4&gt;=1,L4&lt;=IF(F4="&#23460;&#29123;&#29123;&#28903;&#38149;&#28809;&#65288;&#29123;&#27668;&#20919;&#20957;&#65289;",110,100)))'
)
NEW_FORMULA = (
    'OR(L4="",AND(ISNUMBER(L4),L4&gt;=1,L4&lt;=IF(E4="&#23460;&#29123;&#29123;&#28903;&#38149;&#28809;&#65288;&#29123;&#27668;&#20919;&#20957;&#65289;",110,100)))'
)


def repair(source: Path, destination: Path) -> Path:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError("输入和输出路径必须不同，避免覆盖原模板")
    with ZipFile(source, "r") as source_zip:
        names = source_zip.namelist()
        if "xl/worksheets/sheet9.xml" not in names:
            raise ValueError("未找到工业锅炉工作表XML(sheet9.xml)")
        sheet_xml = source_zip.read("xl/worksheets/sheet9.xml").decode("utf-8")
        if sheet_xml.count(OLD_FORMULA) != 1:
            raise ValueError("未找到唯一的旧工业锅炉验证公式，拒绝盲目修改")
        repaired_xml = sheet_xml.replace(OLD_FORMULA, NEW_FORMULA)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(prefix="v4-boiler-", suffix=".xlsx", dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as output_zip:
                for info in source_zip.infolist():
                    payload = repaired_xml.encode("utf-8") if info.filename == "xl/worksheets/sheet9.xml" else source_zip.read(info.filename)
                    output_zip.writestr(info, payload)
            if temporary.stat().st_size <= 0:
                raise ValueError("修复后的模板为空")
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
    return destination


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 2:
        print("用法: python tools/repair_v4_boiler_validation_reference.py 输入.xlsx 输出.xlsx", file=sys.stderr)
        return 2
    try:
        print(repair(Path(args[0]), Path(args[1])))
    except (OSError, ValueError) as exc:
        print(f"修复失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
