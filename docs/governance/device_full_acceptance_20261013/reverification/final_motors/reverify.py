import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
FIRST = ROOT / 'docs/governance/device_full_acceptance_20261013/motors'
sha = lambda b: hashlib.sha256(b).hexdigest()
old = json.loads((FIRST / 'source_manifest.json').read_text('utf-8-sig'))
checks = json.loads((FIRST / 'final_checks.json').read_text('utf-8-sig'))
records = []
for item in old:
    p = Path(item['path'])
    data = p.read_bytes()
    rec = dict(path=str(p), first_sha256=item['sha256'], before_sha256=sha(data))
    rec['unchanged_from_first'] = rec['before_sha256'] == item['sha256']
    if not rec['unchanged_from_first'] and p.name == 'ISSUE_REGISTRATION_REQUEST.md':
        text = data.decode('utf-8-sig').replace('\r\r\n', '\n').replace('\r\n', '\n')
        prefix, suffix = text.split('## 正式编号回链', 1)
        matches = []
        for newline in ['\n', '\r\n']:
            candidate = (prefix.rstrip('\n') + '\n').replace('\n', newline).encode('utf-8')
            if sha(candidate) == item['sha256']:
                matches.append(repr(newline))
        assert matches, p
        rec['semantic_change'] = '仅追加正式编号回链；移除追加段并还原换行后精确恢复首轮SHA'
        rec['original_newline_reconstruction'] = matches
        rec['appended_text'] = '## 正式编号回链' + suffix
    elif not rec['unchanged_from_first']:
        assert p.name == 'STANDARD_ISSUES_REGISTER.md'
        rec['semantic_change'] = '根台账新增登记；本组九条逐项审查，其他标准变化不属于本组结论'
    records.append(rec)

registry = (ROOT / 'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig')
headings = re.findall(r'^### (EQP-STD-[A-Z0-9]+-\d+)\b', registry, re.M)
duplicates = [k for k, v in Counter(headings).items() if v > 1]
assert not duplicates, duplicates
issues = []
type_mismatches = []
expected_types = {'GB18613':['MISSING / IMPLEMENTATION','AMBIGUITY / IMPLEMENTATION','REFERENCE / IMPLEMENTATION','TYPO'], 'GB30254':['REFERENCE / IMPLEMENTATION','MISSING / IMPLEMENTATION'], 'GB30253':['TYPO / CONFLICT','REFERENCE / IMPLEMENTATION','AMBIGUITY / IMPLEMENTATION']}
for folder, prefix, keys in [('gb18613_2020','GB18613',['R01','R02','R03','R04']), ('gb30254_2024','GB30254',['请求1','请求2']), ('gb30253_2024','GB30253',['R1','R2','R3'])]:
    request = ROOT / 'docs/standards' / folder / 'ISSUE_REGISTRATION_REQUEST.md'
    local = request.read_text('utf-8-sig')
    for i,key in enumerate(keys,1):
        stable = f'EQP-STD-{prefix}-{i:03}'
        block = re.search(r'^### '+stable+r'\b[^\n]*\n(.*?)(?=^### |\Z)', registry,re.M|re.S).group(1)
        link = f'docs/standards/{folder}/ISSUE_REGISTRATION_REQUEST.md'
        assert '|状态|`OPEN`|' in block
        assert link in block and request.exists()
        assert stable in local and '../../../STANDARD_ISSUES_REGISTER.md' in local
        assert key in block.replace(' ','')
        assert all(label in block for label in ['标准原文事实/定位','当前技术判断','软件当前处理方式/待决建议'])
        assert '建议内容未获批准' in block
        actual_type = re.search(r'\|问题类型\|([^\n]+)',block).group(1).strip('|')
        expected_type = expected_types[prefix][i-1]
        if expected_type not in actual_type:
            type_mismatches.append(dict(stable_id=stable,actual=actual_type,expected=expected_type))
        issues.append(dict(local_key=key,stable_id=stable,status='OPEN',root_backlink=link,local_backlink='../../../STANDARD_ISSUES_REGISTER.md',no_approval=True,registry_block=block))

evidence = []
for name in ['source_manifest.json','final_checks.json','table_coverage.csv','independent_cell_comparison.csv','mechanical_summary.json','GB18613_2020_ACCEPTANCE.md','GB30254_2024_ACCEPTANCE.md','GB30253_2024_ACCEPTANCE.md']:
    p = FIRST / name
    evidence.append(dict(path=str(p),sha256=sha(p.read_bytes())))
for r in records:
    r['after_sha256'] = sha(Path(r['path']).read_bytes())
    r['stable_during_reverification'] = r['before_sha256'] == r['after_sha256']
assert all(r['stable_during_reverification'] for r in records)
result = dict(head='d9f711068bde583138a7f3dded6f64dcaa339761',locked_central='ee5feb0cc34dbd99790500fadd0c4c932e202a20',scope='三项电机Stage A资料独立复验；非软件支持验收',conclusion='PASS',sources=records,reused_first_evidence=evidence,issues=issues,duplicate_registry_heading_ids=duplicates,coverage=dict(tables=41,power_rows=1019,source_cells=16382,mismatches=0,first_visual_pdf_pages=78),not_run=['重复全量PDF渲染/逐格提取（源字节未变，复用首轮）','生产代码测试/compileall/smoke/性能','外部引用全文适用性验收','软件Stage D验收'])
result['type_mismatches'] = type_mismatches
if type_mismatches:
    result['conclusion'] = 'NEEDS_INFO'
(OUT / 'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(conclusion=result['conclusion'],sources=len(records),unchanged=sum(x['unchanged_from_first'] for x in records),issues=len(issues),stable=all(x['stable_during_reverification'] for x in records)),ensure_ascii=False))
