from pathlib import Path
import re,json,hashlib
p=Path('docs/governance/device_full_acceptance_20261013/reverification/final_hvac');rp=Path('STANDARD_ISSUES_REGISTER.md');raw=rp.read_bytes()
a=(p/'STANDARD_ISSUES_REGISTER_snapshot.txt').read_text(encoding='utf-8-sig');b=raw.decode('utf-8-sig').replace('\r\n','\n');checks=[]
for sid,n in [('29541',5),('19576',2),('37479',3),('21454',4),('19577',6)]:
 for i in range(1,n+1):
  id=f'EQP-STD-GB{sid}-{i:03}'
  def block(t):return re.search(r'^### '+id+r'\b.*?(?=^#{1,3} |\Z)',t,re.M|re.S).group().strip()
  checks.append({'id':id,'unchanged_during_review':block(a)==block(b)})
assert all(x['unchanged_during_review'] for x in checks)
sha=hashlib.sha256(raw).hexdigest();stable=sha==hashlib.sha256(rp.read_bytes()).hexdigest();assert stable
(p/'root_end_snapshot.txt').write_bytes(raw)
(p/'root_scope_stability.json').write_text(json.dumps({'root_whole_file_changed_during_review':True,'reason':'Other standard changes; 20 scoped blocks unchanged after newline normalization','end_sha256':sha,'end_snapshot_stable_on_reread':stable,'scoped_blocks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
f=p/'FINAL_HVAC_REPORT.md';s=f.read_text(encoding='utf-8');s=s.replace('**暂行结论：四项通过；GB29541五个问题类型字段漏转，待定向修复复验。**','**本批结论：GB19576、GB37479、GB21454、GB19577四项Stage A映射资料验收通过；GB29541为 CHANGES_REQUIRED，仅五个已登记问题类型字段漏转待修。**');s=s.replace('首轮四项未登记缺口已补齐；','首轮四项稳定ID/双向回链缺口已补齐，GB29541类型完整性尚缺；');s=s.replace('暂行稳定性见final_stability.json：54受验文件及锁文件稳定，根台账并发改动，尚待修复后锁定最终快照。','稳定性见final_stability.json：54受验文件及锁文件稳定。根台账整文件因并发改动而变化，不声称全程SHA稳定；本组20问题块换行归一后的内容全部未变，末次快照立即重读SHA稳定，见root_scope_stability.json。末次根SHA `'+sha+'`。后续仅对五个类型字段和根SHA短复验，无需重跑未变全量数据。');f.write_text(s,encoding='utf-8');print('PASS stability 20 blocks',sha)
