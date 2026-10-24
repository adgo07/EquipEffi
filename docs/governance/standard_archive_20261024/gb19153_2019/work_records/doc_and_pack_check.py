import json, re, os, collections
from pathlib import Path
import subprocess

BASE = Path(r"G:\Python Project\EquipEffi")
DIR = BASE / "docs/standards/gb19153_2019"

print("=== A. 目录内 Markdown 链接检查 ===")
bad = []
for md in DIR.rglob("*.md"):
    txt = md.read_text(encoding="utf-8")
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", txt):
        target = m.group(2).split("#")[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        p = (md.parent / target).resolve()
        if not p.exists():
            bad.append((str(md.relative_to(BASE)), target))
print(f"  扫描文件数={len(list(DIR.rglob('*.md')))} 断链={len(bad)}")
for b in bad:
    print("   BROKEN", b)

print("\n=== B. git check-ignore（交付文件是否会被忽略）===")
files = [str(p) for p in DIR.rglob("*") if p.is_file() and "node_modules" not in str(p)]
r = subprocess.run(["git", "-C", str(BASE), "check-ignore", "-v", "--"] + files,
                   capture_output=True, text=True)
ignored = [l for l in r.stdout.splitlines() if l.strip()]
print(f"  目录内文件（不含 node_modules）={len(files)}  被忽略={len(ignored)}")
for l in ignored[:12]:
    print("   IGNORED:", l)
print("   --- 非 tmp 的交付文件是否被忽略 ---")
ign = set()
for l in ignored:
    parts = l.split("\t")
    if len(parts) >= 2:
        ign.add(os.path.normcase(os.path.abspath(parts[-1])))
for p in files:
    ap = os.path.normcase(os.path.abspath(p))
    rel = os.path.relpath(p, DIR)
    if ap in ign and not rel.replace("\\", "/").startswith("tmp/"):
        print("   !! 非 tmp 被忽略:", rel)

print("\n=== C. 旧运行时空压机标准包行数 ===")
cj = BASE / "src/equipeffi/resources/standards/compressor.json"
print("  exists:", cj.exists())
if cj.exists():
    d = json.loads(cj.read_text(encoding="utf-8"))
    print("  top keys:", list(d)[:12])
    rows = d.get("rows") or d.get("records") or d.get("data") or []
    print("  rows:", len(rows))
    if rows:
        print("  sample:", json.dumps(rows[0], ensure_ascii=False)[:400])
        c = collections.Counter()
        for r in rows:
            for k in ("table", "table_no", "table_id", "source_table"):
                if k in r:
                    c[(k, r[k])] += 1
                    break
        print("  table dist:", c.most_common(10))
