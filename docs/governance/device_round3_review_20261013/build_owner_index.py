import json, hashlib
from pathlib import Path

out=Path(__file__).resolve().parent
groups=['motors','compressor_boiler','hvac','fans_submersible']
root=json.loads((out/'ROOT_ISSUES_START.json').read_text(encoding='utf-8'))
expected={x['id'] for x in root if x['in_formal_15_scope']}
items=[]; manifests=[]
for g in groups:
    p=out/g/'owner_items.json'
    manifests.append({'path':p.relative_to(out).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for x in json.loads(p.read_text(encoding='utf-8')):
        items.append(dict(x, review_group=g, source_detail=p.relative_to(out).as_posix()))
actual={x.get('existing_issue_id') for x in items if x.get('existing_issue_id')}
assert actual==expected, (expected-actual,actual-expected)
assert len({(x['review_group'],x['id']) for x in items})==len(items)
(out/'OWNER_ALL_ITEMS.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
def fmt(v):
    return json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else str(v or '见组专属证据，未取得额外批准')
parts=['# 15份标准全部待核事项：Owner阅读入口',
'''本清单覆盖根台账正式范围62个唯一既有编号，保留其OPEN状态。组清单共103行，其中64行关联62个既有编号（两行是既有条目的细分），39行尚无正式编号。39行还包含跨标准重复、运行资产事实差异和普通实现设计事项，**不是39个新标准错误，也不是39项必须重新批准**。逐项完整字段与源SHA保留于 OWNER_ALL_ITEMS.json。泵2项、变压器9项不在正式范围，不重开已有确认。

仅“标准解释会改变正式结果、范围变化、Golden真值、Frozen升级、破坏性迁移、正式发布、支持提升”等既有七类规则需要Owner决策。原文明确的事实维护、索引修正、元数据清理和常规实现选择不另造审批。下列问题句是供集中审阅，不代表每项都构成审批门禁；可先确认需补证据的事项，不必一次决定所有解释。

跨标准24项另见 cross_standard/CROSS_STANDARD_REVIEW.md，其中O1重复G1、H1重复O2；部分已在组候选中，不能与本表相加。新增候选未写入正式台账，编号LOCAL仅为本报告导航。''',
'## 已有根编号（62个）']
for g in groups:
    subset=[x for x in items if x['review_group']==g and x['id'] in expected]
    parts.append(f'### {g}（{len(subset)}个）')
    for x in subset:
        ident=x['id']; loc=x.get('source_location',x.get('original_excerpt_and_location',''))
        excerpt=x.get('original_excerpt',x.get('root_record_fact',x.get('source_excerpt','')))
        parts.extend([f'#### {ident}',
            f"原文与出处：{fmt(loc)} {fmt(excerpt) if excerpt else ''}",
            f"疑点：{fmt(x.get('ambiguity'))}",f"影响：{fmt(x.get('impact'))}",
            f"候选：{fmt(x.get('options',x.get('alternatives')))}",
            f"建议：{fmt(x.get('recommendation'))}",
            f"证据强度：{fmt(x.get('evidence_strength'))}；批准状态：{fmt(x.get('approval_status'))}",
            f"请核：{fmt(x.get('owner_question'))}",
            f"详细证据：[{g}/owner_items.json]({g}/owner_items.json)，同ID条目。"])
parts.append('## 细分、补充及尚未正式登记的候选（41行，不是41个新Issue）')
for x in items:
    if x['id'] in expected: continue
    parts.extend([f"### {x['id']}（{x['review_group']}）",f"关联既有编号：{x.get('existing_issue_id') or '无；尚未正式登记'}。",
        f"出处/摘录：{fmt(x.get('source_location',x.get('original_excerpt_and_location')))} {fmt(x.get('original_excerpt',x.get('source_excerpt',''))) if x.get('original_excerpt',x.get('source_excerpt')) else ''}",
        f"疑点：{fmt(x.get('ambiguity'))}；影响：{fmt(x.get('impact'))}",
        f"候选：{fmt(x.get('options',x.get('alternatives')))}；建议：{fmt(x.get('recommendation'))}",
        f"证据：{fmt(x.get('evidence_strength'))}；批准状态：{fmt(x.get('approval_status'))}",f"请核：{fmt(x.get('owner_question'))}",
        f"原始详细项：[{x['source_detail']}]({x['source_detail']})。"])
(out/'OWNER_REVIEW_INDEX.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
check={'expected_root_ids':len(expected),'unique_existing_ids':len(actual),'group_rows':len(items),'rows_linking_existing':sum(bool(x.get('existing_issue_id')) for x in items),'unregistered_rows':sum(not x.get('existing_issue_id') for x in items),'missing':sorted(expected-actual),'extra':sorted(actual-expected),'group_sources':manifests}
(out/'OWNER_COVERAGE_CHECK.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in check.items() if k!='group_sources'},ensure_ascii=False))
