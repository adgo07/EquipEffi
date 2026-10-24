"""Read group review outputs only; write coverage evidence in this directory."""
import collections
import datetime
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent.parent
required = ['id', 'standard', 'source_location', 'ambiguity', 'impact', 'options',
            'recommendation', 'evidence_strength', 'approval_status', 'owner_question',
            'source_opinion_ids']
root = json.loads((base / 'ROOT_ISSUES_START.json').read_text(encoding='utf-8'))
expected = {x['id'] for x in root if x['in_formal_15_scope']}
all_items, groups = [], {}
for group in ['motors', 'compressor_boiler', 'hvac', 'fans_submersible']:
    path = base / group / 'owner_items.json'
    data = path.read_bytes()
    items = json.loads(data)
    ids = [x['id'] for x in items]
    existing = [x.get('existing_issue_id') for x in items if x.get('existing_issue_id')]
    groups[group] = {
        'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
        'rows': len(items), 'existing_unique': len(set(existing)),
        'missing_fields': [{'id': x.get('id'), 'fields': [k for k in required if not x.get(k)]}
                           for x in items if any(not x.get(k) for k in required)],
        'duplicate_ids': [k for k, v in collections.Counter(ids).items() if v > 1],
    }
    all_items.extend(items)
actual_list = [x['existing_issue_id'] for x in all_items if x.get('existing_issue_id')]
actual = set(actual_list)
result = {
    'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'meaning': 'Completeness of review index and fields, not proof that interpretations are approved',
    'groups': groups, 'expected_existing': len(expected), 'actual_existing': len(actual),
    'missing_existing': sorted(expected-actual), 'unexpected_existing': sorted(actual-expected),
    'duplicate_existing_rows': [k for k,v in collections.Counter(actual_list).items() if v > 1],
    'candidate_rows': len(all_items)-len(actual_list),
    'candidate_note': 'LOCAL rows include cross-standard overlaps and routine design/maintenance; not a count of new standard errors or required Owner approvals',
}
opinion_files = {
    'motors': ('original_opinions.json', 28),
    'compressor_boiler': ('findings.json', 15),
    'fans_submersible': ('round3_findings.json', 16),
}
result['original_opinion_coverage'] = {}
for group, (name, count) in opinion_files.items():
    path = base/group/name
    data = path.read_bytes()
    rows = json.loads(data)
    result['original_opinion_coverage'][group] = {
        'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
        'rows': len(rows), 'expected_rows': count,
        'note': 'motors includes 18 historical plus 10 R3; compressor includes 11 R3 plus 4 extensions; fans lists 16 R3 original rows, inherited separately',
    }
path = base/'hvac'/'claim_verification.json'
data = path.read_bytes()
rows = json.loads(data)
result['original_opinion_coverage']['hvac'] = {
    'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
    'r3_rows': len(rows['claims']), 'historical_rows': len(rows['history_crosswalk']),
    'r3_verbatim_rows': sum(bool(x.get('original_source_row')) for x in rows['claims']),
    'historical_verbatim_rows': sum(bool(x.get('verbatim_opinion_row')) for x in rows['history_crosswalk']),
}
(base/'coordinator'/'GROUP_COVERAGE_CHECK.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
