"""Read-only verification of the saved revision snapshot; run from any directory."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    manifest = json.loads((HERE / 'FILE_CHANGES.json').read_text(encoding='utf-8'))
    decisions = json.loads((HERE / 'DECISION_APPLICATION.json').read_text(encoding='utf-8'))
    protected = json.loads((HERE / 'PROTECTED_HASHES.json').read_text(encoding='utf-8'))
    errors = []
    for entry in manifest['files']:
        path = ROOT / entry['path']
        if not path.is_file() or sha(path) != entry['after_sha256']:
            errors.append('revision_hash: ' + entry['path'])
        if path.suffix == '.md' and path.name != 'OWNER_REPLY_SNAPSHOT.md':
            for href in re.findall(r'\]\(([^\n)]+)\)', path.read_text(encoding='utf-8-sig')):
                href = unquote(href.strip('<>').split('#')[0])
                if not href or re.match(r'\w+://', href) or href.startswith('mailto:'):
                    continue
                if not (path.parent / href).exists():
                    errors.append('link: ' + entry['path'] + ' -> ' + href)
    for rel, expected in protected.items():
        path = ROOT / rel
        if not path.is_file() or sha(path) != expected:
            errors.append('protected_hash: ' + rel)
    register = (ROOT / 'STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8')
    ids = [i['id'] for i in decisions['items']]
    if len(ids) != 25 or len(set(ids)) != 25:
        errors.append('decision_count')
    for item in decisions['items']:
        pattern = r'^### ' + re.escape(item['id']) + r'[^\n]*\n(.*?)(?=^### |\Z)'
        match = re.search(pattern, register, re.M | re.S)
        if not match or f"|状态|`{item['status']}`|" not in match.group(1):
            errors.append('issue_status: ' + item['id'])
        mapping = (ROOT / 'docs/standards' / item['key'] / 'STANDARD_MAPPING.md').read_text(encoding='utf-8')
        if item['id'] not in mapping or item['rule'] not in mapping:
            errors.append('mapping_decision: ' + item['id'])
    return {'errors': errors, 'protected_files': len(protected), 'revision_files': len(manifest['files']), 'decisions': len(ids)}

if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['errors']))
