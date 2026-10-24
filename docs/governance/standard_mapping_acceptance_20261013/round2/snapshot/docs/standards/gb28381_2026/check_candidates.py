"""Exact rational checks of Appendix A examples; no approved runtime precision."""
from fractions import Fraction as F
from pathlib import Path
import json
root=Path(__file__).resolve().parent
lerp=lambda a,b,t:a+(b-a)*t
a1=lerp(F('82.35'),F('82.60'),F(120,170))
p=(F('124.11')-98)/(F('127.4')-98)
corners=[('188.8','199.8','182.6','194.2'),('198.2','209.8','191.7','203.9'),('207.7','219.8','200.9','213.6')]
a2=[]
for values in corners:
    a,b,c,d=map(F,values)
    a2.append(lerp(lerp(a,b,p),lerp(c,d,p),F(3,4)))
assert a1-4 <= F('80.49') < a1
assert a2[0] < 195 <= a2[1]
result={'method':'exact rational arithmetic; not a runtime Numeric Profile','A1_level1_fraction':str(a1),'A1_level1_decimal_preview':str(float(a1)),'A1_grade':2,'A2_threshold_fractions':[str(v) for v in a2],'A2_decimal_previews':[str(float(v)) for v in a2],'A2_grade':2,'pass':2,'fail':0,'error':0,'skip':0,'not_run':'Other 28 candidate rows are designed, not executable runtime tests.'}
(root/'CANDIDATE_CHECKS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
