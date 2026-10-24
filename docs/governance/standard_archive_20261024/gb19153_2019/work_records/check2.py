import json, re
from pathlib import Path

BASE = Path(r"G:\Python Project\EquipEffi")
DIR = BASE / "docs/standards/gb19153_2019"

print("=== A. 交付 Markdown 链接检查（排除 tmp）===")
mds = [p for p in DIR.rglob("*.md") if "tmp" not in p.parts]
bad = []
for md in mds:
    txt = md.read_text(encoding="utf-8")
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", txt):
        target = m.group(2).split("#")[0].strip()
        if not target or "://" in target:
            continue
        p = (md.parent / target).resolve()
        if not p.exists():
            bad.append((md.name, target))
print("  文件:", [p.name for p in mds])
print("  断链:", bad if bad else "0")

print("\n=== B. 旧标准包 表4 18.5/22 kW 0.7-1.4 MPa 行 ===")
d = json.loads((BASE / "src/equipeffi/resources/standards/compressor.json").read_text(encoding="utf-8"))
print("  standard_code:", d.get("standard_code"), "| effective_date:", d.get("effective_date"),
      "| unit_note:", d.get("unit_note"))
rows = [r for r in d["rows"] if r["table"] == "表4" and r["power_kw"] in (18.5, 22)
        and r["pressure_mpa"] in (0.7, 0.8, 1.0, 1.25, 1.4)]
rows.sort(key=lambda r: (r["power_kw"], r["level"], r["pressure_mpa"]))
for r in rows:
    print("   ", json.dumps(r, ensure_ascii=False))
print("  小计:", len(rows), "（新映射对应组合数=2功率×3等级×5压力×2分支=60）")
print("\n  legacy 表4 全部键样例:", json.dumps(d["rows"][1008 + 756 + 432], ensure_ascii=False))
print("  legacy 表4 是否有 bracket/液冷字段:", sorted({k for r in d["rows"] if r["table"] == "表4" for k in r}))
print("  legacy 表4 cooling 取值:", sorted({str(r.get("cooling")) for r in d["rows"] if r["table"] == "表4"}))
