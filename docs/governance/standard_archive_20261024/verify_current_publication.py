"""Recheck archive delivery, retaining the original publication checker as history."""
from pathlib import Path
import json, subprocess
R = Path.cwd()
A = R / 'docs/governance/standard_archive_20261024'
source = (A / 'verify_publication.py').read_text(encoding='utf-8')
# Keep the historical script and receipt unchanged; capture its result in memory.
source = source[:source.index("(A/'PUBLICATION_VALIDATION.json').write_text")]
ns = {}
exec(compile(source, 'verify_publication.py', 'exec'), ns)
old = ns['result']
expected = [e for e in old['errors'] if e == 'manifest docs/standards/gb18613_2020/STANDARD_MAPPING.md' or e.startswith('gb18613_2020 missing content ') or e in {'Owner rule EQP-STD-GB18613-001', 'Owner rule EQP-STD-GB18613-002', 'Owner rule EQP-STD-GB18613-003', 'Owner rule EQP-STD-GB18613-004'}]
errors = [e for e in old['errors'] if e not in expected]
# Replacement is permitted only when the independently reviewed A.2 payload hashes pass.
gb = json.loads(subprocess.check_output(['python', str(R/'docs/governance/gb18613_acceptance_20261024/verify_delivery.py'), str(R)], text=True, encoding='utf-8'))
fixed = ['DELIVERY_HASHES.json','A2_REVIEW.md','A2_GIT_REVIEW.md','ARCHIVE_MANIFEST.json']
for name in fixed:
    path = 'docs/governance/gb18613_acceptance_20261024/' + name
    original = subprocess.check_output(['git','show','d4c811a06c2f0a4ae20eccfc0e135c56d3dffc60:'+path])
    if (R/path).read_bytes() != original: errors.append('Acceptance evidence changed: '+path)
initial = 'f9ab7b6e2593f5ca2a56538ba766bfb409b2d530'
other = [str(p.relative_to(R)).replace('\\','/') for p in (R/'docs/standards').iterdir() if p.is_dir() and p.name != 'gb18613_2020']
changed = subprocess.check_output(['git','diff','--name-only',initial,'--',*other], text=True, encoding='utf-8').strip()
other_unchanged = not changed
if changed: errors.append('Other standard directories changed since initial import: '+changed)
protected = ['specs','tests','.github','platform-lock.json','V1_SCOPE.md','docs/standards/gb19762_2025','docs/standards/gb20052_2024','docs/standards/gb20052_v21']
changed = subprocess.check_output(['git','diff','--name-only',old['publication_base'],'--',*protected],text=True,encoding='utf-8').strip()
if changed: errors.append('Protected or software validation paths changed: '+changed)
src = subprocess.check_output(['git','diff','--name-only',old['publication_base'],'--','src'],text=True,encoding='utf-8').splitlines()
if src != ['src/equipeffi/resources/knowledge/motor_efficiency_tolerance_owner_20261024.md']: errors.append('Unexpected production changes: '+repr(src))
result = dict(status='PASS' if not errors else 'FAIL', errors=errors, publication_base=old['publication_base'], manifest_entries=old['manifest_entries'], historical_gb18613_checks_superseded=len(expected), replacement_evidence='docs/governance/gb18613_acceptance_20261024/DELIVERY_HASHES.json and A2_REVIEW.md', other_standards_unchanged=other_unchanged, active_local_links_checked=old['active_local_links_checked'], grade_values_compared=old['grade_values_compared'], gb18613=gb, protected_and_runtime='PASS' if not errors else 'FAIL', production_tests='NOT_RUN locally; final-head Windows Core CI required before merge', pdf_reverification='NOT_RUN; existing same-hash evidence retained')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
