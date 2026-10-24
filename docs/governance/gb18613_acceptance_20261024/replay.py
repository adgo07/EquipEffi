"""Run the preserved audit with explicit paths and a new output directory."""
import argparse
import ast
import hashlib
from pathlib import Path

p = argparse.ArgumentParser()
for name in ("pdf", "workbook", "output"):
    p.add_argument("--" + name, required=True, type=Path)
a = p.parse_args()
for path, expected in ((a.pdf, "ba617a76b79cecdda57fab3950ecccaecbb1b2997645192f0429395468167304"), (a.workbook, "fabb5722cf73afbdaf8fa8c5e76b8eddc86918b4cffe5ce060594afc609164bb")):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        p.error("Source SHA mismatch: " + str(path))
if a.output.exists():
    p.error("Output must be a new directory")
script = Path(__file__).with_name("compare_cells.py")
tree = ast.parse(script.read_text(encoding="utf-8-sig"))
paths = {"PDF": a.pdf, "WB": a.workbook, "OUT": a.output}
found = set()
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in paths:
        name = node.targets[0].id
        node.value = ast.Constant(str(paths[name].resolve()))
        found.add(name)
if found != set(paths):
    raise RuntimeError("Historical script path assignments changed")
exec(compile(ast.fix_missing_locations(tree), str(script), "exec"), {"__name__": "__main__", "__file__": str(script)})
