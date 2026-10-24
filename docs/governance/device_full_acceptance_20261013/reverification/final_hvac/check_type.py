from pathlib import Path
import re,json,hashlib
p=Path('docs/governance/device_full_acceptance_20261013/reverification/final_hvac')
s=Path('STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8-sig');out=[]
for i,expected in enumerate(['MISSING / AMBIGUITY','MISSING / AMBIGUITY','IMPLEMENTATION / REFERENCE','REFERENCE','AMBIGUITY'],1):
 id=f'EQP-STD-GB29541-{i:03}';b=re.search(r'^### '+id+r'\b.*?(?=^#{1,3} |\Z)',s,re.M|re.S).group()
 actual=re.search(r'\|问题类型\|([^\n]+)\|',b).group(1).strip('` ')
 ok=all(x in actual for x in expected.split(' / ')) and '待确认' not in actual
 out.append({'id':id,'expected_original_request_type':expected,'actual_root_type':actual,'pass':ok})
(p/'type_recheck.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
