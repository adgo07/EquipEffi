"""Read-only source capture for the third-party opinion review."""
import collections
import datetime
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
previous = ROOT / 'docs/governance/device_full_acceptance_20261013'
formal = json.loads((previous / 'reverification/final_source_manifest.json').read_text(encoding='utf-8'))
paths = {ROOT / f['relative_path'] for f in formal['files']}
extra = [
    'AGENTS.md', 'platform-lock.json', 'HANDOFF.md', 'TASK_STATE.md',
    'docs/standards/README.md',
    'docs/governance/SIX_STANDARD_MAPPING_COORDINATION_20261013.md',
    'src/equipeffi/resources/standards/gb30253_2024_pdf_verified_v1.json',
]
paths.update(ROOT / p for p in extra)
review = ROOT / '_acceptance_20261013'
paths.update(review.glob('*.md'))
paths.update((review / 'round3').glob('*.md'))
paths.update((review / 'round3/evidence_snapshots').glob('*.txt'))
files = []
for path in sorted(paths):
    if path.is_file():
        data = path.read_bytes()
        files.append({'relative_path': path.relative_to(ROOT).as_posix(),
                      'absolute_path': str(path), 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest()})
text = (ROOT / 'STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8-sig')
blocks = re.split(r'(?m)^### (?=EQP-STD-)', text)[1:]
issues = []
for block in blocks:
    ident = re.match(r'(EQP-STD-[A-Z0-9]+-\d+)', block)
    if not ident:
        continue
    fields = {}
    for line in block.splitlines():
        cells = line.strip().strip('|').split('|')
        if line.startswith('|') and len(cells) >= 2:
            fields[cells[0].strip()] = '|'.join(cells[1:]).strip()
    issues.append({'id': ident.group(1), 'title': block.splitlines()[0],
                   'in_formal_15_scope': not ident.group(1).startswith(('EQP-STD-GB19762-', 'EQP-STD-GB20052-')),
                   'fields': fields})
report = {'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'repository': 'https://github.com/adgo07/EquipEffi.git',
          'head': 'd9f711068bde583138a7f3dded6f64dcaa339761',
          'locked_central_sha': 'ee5feb0cc34dbd99790500fadd0c4c932e202a20',
          'fetch': 'Succeeded on authorized escalation; initial sandbox FETCH_HEAD access denied',
          'origin_master': '2c7807f32ef08d18554014328efd4ceaa356726f',
          'head_ahead_behind_origin_master': [1, 0],
          'local_master_ahead_behind_origin_master': [0, 46],
          'scope': '15 new standards; pump and transformer supplementary only',
          'files': files}
(OUT / 'INPUT_MANIFEST.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'ROOT_ISSUES_START.json').write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'ROOT_REGISTER_START.txt').write_bytes((ROOT / 'STANDARD_ISSUES_REGISTER.md').read_bytes())
print(json.dumps({'files': len(files), 'root_issue_count': len(issues),
                  'formal_scope_issue_count': sum(i['in_formal_15_scope'] for i in issues),
                  'standard_counts': dict(collections.Counter(i['id'].rsplit('-', 1)[0] for i in issues))}, ensure_ascii=False))
