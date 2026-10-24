from pathlib import Path
import json
b=Path('docs/governance/device_full_acceptance_20261013')
p=b/'ACCEPTANCE_SUMMARY.md'; s=p.read_text(encoding='utf8')
s=s.replace('状态：**首轮独立验收完成；17项不全部PASS，问题修复及登记后需按新SHA复验**。','状态：**当前正式范围为15项新编标准、128张原文表；首轮核验完成，GB/T36561修复及48项登记后需定向复验。**')
s=s.replace('## 审计对象、预检查与方法','''## 最新范围纠正（优先于本文历史范围）

用户确认泵和变压器早已确认，不属于本轮正式验收。**正式范围仅15项新编标准版本、128表（166−泵3−变压器35）**。首轮实际额外查看17版本/166表的事实与旧SHA证据保留，不追溯删除或改写；泵/变压器原确认状态继续有效，额外发现仅列查漏补缺建议，撤销其本轮必修/重验身份，不阻断15项验收，不安排二者复验。此前修复候选只作为候选保留，不替换已确认资产。

## 首轮实际审计对象、预检查与方法''')
s=s.replace('## 逐标准结果','## 正式15项逐标准结果')
lines=s.splitlines(); supplements=[]; kept=[]
for line in lines:
 if line.startswith('|GB19762—2025') or line.startswith('|GB20052—2024'):
  supplements.append(line); continue
 kept.append(line)
s='\n'.join(kept)
s=s.replace('2. GB19762：PUMP-A01—A05为完整主映射缺漏和原文附录矛盾。','2. 【正式范围外补充查漏，不是本轮必修】GB19762：PUMP-A01—A05为额外复查建议和原文附录疑点。')
s=s.replace('3. GB20052：TR-F01为24表辅助阻抗参数未完整进入冻结二件套，不是损耗错值；须Owner针对具体变更批准后新版本保留旧SHA，不能直接补写/重存V2.1。','3. 【正式范围外补充查漏，不是本轮必修】GB20052：TR-F01为24表辅助阻抗参数补全建议，不是损耗错值；原确认有效，本轮不要求新版本或重验，候选保留，不能据额外复查替换V2.1。')
s=s.replace('17版本合计166张原文表已逐表覆盖','首轮实际17版本合计166张原文表已逐表覆盖（其中正式15版本128表，另泵/变压器38表为补充查漏）')
s=s.replace('泵及变压器为完整性缺口。','泵及变压器的额外查漏不计入正式15项缺陷或阻断。')
s+='''

## 正式范围外附件（不重开原确认）

|已有标准|补充查漏附件|当前地位|
|---|---|---|
|GB19762—2025两泵分支|[额外复查证据](pump/PUMP_ACCEPTANCE.md)|原确认有效；A01—A05仅查漏建议，旧报告范围结论已由本最新说明限缩|
|GB20052—2024|[额外复查证据](transformer/ACCEPTANCE_REPORT.md)|原确认/冻结继续有效；TR-F01仅补充建议，候选不自动取代原版；不阻断15项|
'''
p.write_text(s+'\n',encoding='utf8')
p=b/'DEVICE_INDEPENDENT_INDEX.md';s=p.read_text(encoding='utf8')
s=s.replace('范围仍为2026-10-13北京时间17个设备标准版本、166原文表','正式范围按用户最新纠正为2026-10-13北京时间15个新编设备标准版本、128原文表；首轮实际17项/166表中，泵及变压器另作补充查漏附件')
s=s.replace('**当前没有全部修复完成或全部复验PASS结论。**','**当前正式15项尚未全部复验PASS；泵和变压器原确认有效，不属于本轮必修或复验范围。**')
ls=[]
for line in s.splitlines():
 if line.startswith('|gb19762_2025|') or line.startswith('|gb20052_2024|') or line.startswith('|gb20052_v21|') or line.startswith('|泵|') or line.startswith('|变压器|'):continue
 ls.append(line)
s='\n'.join(ls)
s=s.replace('- 变压器新版本仅忠实补录24表辅助技术参数，不新增能效门禁，不改已批准容量状态、±10%选组、同阈值多匹配、D-06温度换算DEFERRED；不重新冻结。旧V2.1及SHA保留。','- 泵/变压器退出正式验收及修复批次，原确认有效。额外查漏附件只作建议，已有候选不替换已确认版本；不安排重验，不阻断15项。')
s+='''

## 范围外补充查漏附件

[泵额外复查](pump/PUMP_ACCEPTANCE.md)、[变压器额外复查](transformer/ACCEPTANCE_REPORT.md)保留历史证据，原确认继续有效。其旧报告中的CHANGES_REQUIRED/NEEDS_COMPLETION仅描述此前扩展核查口径，**不适用于本轮正式15项验收，不重开原验收、不构成本轮必修**。各自原资产路径与旧SHA仍可由首轮清单追溯。
'''
p.write_text(s+'\n',encoding='utf8')
p=b/'reverification/independent_index.json';d=json.loads(p.read_text(encoding='utf8'))
d['formal_scope_count']=15;d['formal_table_count']=128;d['scope_correction']='User clarified pump and transformer are already confirmed; supplemental gap review only, non-blocking, no reacceptance.'
a=[i for i in d['standards'] if '19762' in i['standard'] or '20052' in i['standard']]
d['standards']=[i for i in d['standards'] if i not in a]
for i in a:i['reverification_status']='OUT_OF_FORMAL_SCOPE_PRIOR_ACCEPTANCE_PRESERVED';i['blocking_formal_acceptance']=False
d['supplemental_reviews']=a
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('formal',len(d['standards']),'supplemental',len(a))

