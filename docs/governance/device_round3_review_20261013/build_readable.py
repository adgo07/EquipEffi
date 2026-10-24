import re,json,hashlib,html
from pathlib import Path
from html.parser import HTMLParser

p=Path(__file__).resolve().parent
src=p/'OWNER_REVIEW_INDEX.md'
before=hashlib.sha256(src.read_bytes()).hexdigest()
text=src.read_text(encoding='utf-8')
items=json.loads((p/'OWNER_ALL_ITEMS.json').read_text(encoding='utf-8'))
edits={}
for line in (p/'readable_edits.txt').read_text(encoding='utf-8').splitlines():
    n,fact,doubt=line.split('|',2)
    edits[items[int(n)]['id']]=(fact,doubt,int(n))
assert len(edits)==103
locs={
0:'PDF第5页（印刷第3页），表3，2200 W、4极、1级。',
1:'PDF第7～8页（印刷第5～6页），表6及第6章。',
2:'PDF第3页，第2、4章；第8页，第5.2条。',
3:'PDF第7页（印刷第5页），表6，75 W、转速>1300档。',
4:'PDF第5～6页（印刷第1～2页），第2、4、5章。',
5:'PDF第5页，第1、4章；第8～11、13页的表1～3缺值处；第16～18页的表5、6。',
6:'PDF第7页（印刷第3页），表1，55 kW、12极。',
8:'PDF第6页，第4章；第15～20页，表8～10；第50～51页，表29。',
9:'PDF第7页，表1；运行数据差异详见原清单同编号证据。',
25:'PDF第17页，表7及其后说明。',
28:'PDF第13页，表4；差异明细见 compressor_boiler/runtime_discrepancies.json。',
29:'PDF第6页，表4的天然气左右两栏。',
58:'PDF第9页，表A.1、A.2；第14页，式A.9；工作簿相应负荷率列。',
71:'第4章a)3)～5)、b)3)～6)：PDF第4页（印刷第2页）；第5.3条：PDF第7～8页。',
72:'第4章b)1)、4)、5)及第5.3条b)：PDF第4、8页。',
73:'第5.3条总句：PDF第7页；第4章、表1～4及第5.2条。',
74:'表1～8：PDF第4～8页（印刷第2～6页）。',
75:'第5.3.2、5.4.2条：PDF第4、6页（印刷第2、4页）。',
76:'第1、4章及第5.3.2、5.4.2条：PDF第3、4、6页。',
77:'第2、4章：PDF第3页；第6章：PDF第9页。',
78:'第5.2条：PDF第4页（印刷第2页）。',
79:'表2～4：PDF第5～6页（印刷第3～4页）。',
80:'第7.3.2条，式(1)：PDF第20页（印刷第16页）。',
81:'式(1)、(3)：PDF第20页；式(4)：PDF第21页。',
82:'第7.4.2条：PDF第21页（印刷第17页）。',
83:'第7.5条，式(5)：PDF第21页（印刷第17页）。',
84:'第5章：PDF第7页；表4～6及附录A.2。',
85:'附录A.1、A.2：PDF第22～23页（印刷第18～19页）。',
86:'用户提供的“标准原文/10.潜水电泵相关/”目录；尚未据此形成正式规则。',
87:'第7.2条：PDF第13页；表8、9：PDF第11～12页。',
88:'表9：PDF第12页（印刷第9页）。',
89:'表15：PDF第17页；第9.2.3～9.2.4条：PDF第19页。',
90:'表A.5：PDF第23页（印刷第20页）。',
91:'表A.8、A.11：PDF第24、26页（印刷第21、23页）。',
92:'第7.1.2条注3及第7.1.4条：PDF第12页；附录A.3、A.7和表A.12：PDF第21～26页。',
93:'表16及第9.2.6条：PDF第18～20页（印刷第15～17页）。',
94:'表11：PDF第14页；表A.4：PDF第22页。',
95:'表12注1：PDF第15页（印刷第12页）。',
96:'式(A.2)、表A.2和表A.3：PDF第21～22页。',
97:'表15：PDF第17页；第2章：PDF第4页；第7.3、7.5条：PDF第13～14页。',
98:'2012版PDF第3页，第1章；第4、6页，表1、表5标题。',
99:'2012版PDF第4、6页，第5.3.1、5.4.1条；2026版PDF第20页，第7.1条。',
100:'GB19761相关条款；GB28381—2026 PDF第7页，第5章。',
101:'2012版适用范围；2026版第1章。',
102:'GB19761、GB28381—2012及GB28381—2026各第1章；原清单所引旧审计分类建议。',
}
locs.update({
7:'PDF第5页，第2章；第6页，第4章。',
10:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
11:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
12:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
13:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
14:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
15:'GB18613 PDF第3页、GB30254和GB30253 PDF第5页，各第1章。',
16:'GB18613 PDF第3页及表6；GB30253 PDF第5页，第1章c项和第3.2条。',
17:'GB18613 PDF第3页（印刷第1页），第1章。',
18:'GB18613 PDF第3页、GB30254 PDF第5页、GB30253 PDF第6页，各第4章；对应主映射第5节。',
19:'GB18613 PDF第5～7页；GB30253 PDF第5、7页，范围及表1；对应主映射第4、6节。',
20:'GB18613 PDF第8页、GB30254和GB30253 PDF第6页，各第6章。',
21:'PDF第3页，前言c项；第6页，第5章。',
22:'PDF第3、4、16页，第1章、第4.3及6.1d条；表1～6。',
23:'PDF第4页，第4.3a条；第7、10页，相关表末。',
24:'PDF第16～17页，第6.3.3、6.5.2条，式(3)、(4)及表7。',
26:'PDF第5页，表3后文；第6页，第5.1条。',
27:'PDF第3页，第4章。',
30:'PDF第6页，第5.2条；工作簿“限定值与来源”表。',
31:'PDF第4页表1、第5页表2，燃料品种与特性栏。',
32:'PDF第4页表1、第5页表3，D或Q条件。',
33:'PDF第16页，第6.3条，式(1)、(2)及映射输入说明。',
34:'PDF第3页引用、第4页第4.3b条、第16和18页的测试及附录内容。',
35:'PDF第3页规范性引用、第6章及来源核验记录。',
36:'压缩机、锅炉映射中的数值处理与边界候选章节。',
37:'边界候选BC22；PDF第5～6页，设计效率相关条款。',
38:'PDF第4页，表1及第4.2条。',
39:'PDF第4页，表1及第4.2条。',
40:'PDF第4页，第7章。',
41:'PDF第3页，第2、3章；第4页，第7章。',
42:'PDF第4页（印刷第2页），表1及第4.3条第二段。',
43:'PDF第1页封面；既有延期证据所引国标委发〔2020〕15号。',
44:'PDF第3页，第2章；第4页，第6.4条及表1。',
45:'PDF第4页，第5.1条及表1、表2。',
46:'PDF第1页封面；既有延期附件第3页第4项。',
47:'PDF第3页，第2章；第5页，第6.1～6.3条。',
48:'PDF第3页，第3.1条；第4页，表1注；第4～5页，第4.4条及表3。',
49:'PDF第6页，第5.6b、6.1.2及6.1.3条。',
50:'PDF第9～10页，附录表；第13页，式A.5、A.6及相关定义。',
51:'PDF第3页，第2章；第4～5页表注；第6～7页第6章；第11、13、14页附录引用。',
52:'PDF第8页，第3.4条；第9页，第4.2条；第11页，表5。',
53:'PDF第9页，第4.2条及表1、表2；第10、12页，表3、表7、表8。',
54:'PDF第14页，表A.1；第16页，A.4.2的b、c项。',
55:'PDF第13页，第5.3条注。',
56:'PDF第7、13页，第2、6章；第11页，表5、表6；第16页，A.3、A.4及式A.7、A.13。',
57:'PDF第5页，前言。',
59:'PDF第5页，第6.2条。',
60:'本地PDF第4页，第6.4条后结束线；旧报告所引出版页数信息。',
61:'PDF第3页表1、第4页机房指标文字及第6.2条。',
62:'PDF第3页，第4章；第5页，第5.4a条。',
63:'GB19576和GB37479各PDF第3页，第1章。',
64:'GB19576 PDF第3页范围条款；原清单所列其他标准范围。',
65:'GB19576 PDF第3～4页表1；GB37479 PDF第4页表1。',
66:'GB21454 PDF第3页范围、第4～5页表注及第11页；GB37479 PDF第3页范围。',
67:'GB19576 PDF第4页表1；GB19577 PDF第8页第3.6条及第9页对应表。',
68:'PDF第3页，第1章；第4页，机房专用型及普通分支表行。',
69:'PDF第16页，式A.13相关文字。',
70:'本地PDF的SHA及元数据；原审阅所用47页资料。',
})
extras={
20:'GB18613涉及B法、直接法及铭牌最高转速；GB30254规定P≤2000 kW用B法，>2000 kW用H法；GB30253分别涉及异步启动A法、变频型额定转矩下90%额定转速，以及电梯用电机额定功率测试。',
28:'原清单举例保留的三个普通值及方括号液冷值分别为7.3[6.7]、7.8[7.1]、8.8[7.4]，准确组合定位见差异明细。',
29:'右栏三档分别为103a(93b)、101a(91b)、98a(88b)，字母对应原表脚注。',
33:'原公式为eVC=K14×Pcorr/qcorr。',
41:'所引版本为GB/T 21362—2008和GB/T 23137—2008。',
44:'另两份注明年份的引用为GB/T 19413—2010和JB/T 11968—2014。',
52:'例如0.4 MPa下，1～3级依次为1.05、1.10、1.19。',
56:'表6H1a～H5b工况由GB/T 25861承载；A.3只列A、B、C、D四点，A.7却使用COPbin(43)。',
72:'带扩散筒所指具体条件为0.55≤γ<0.75、机号≥No10；89.5、87、82对应动叶可调且无进气箱、无扩散筒的情形。',
74:'比值档示例为<0.020、0.021～0.030、0.031～0.040及>0.091。',
79:'原记录的例值包括表2的70.0、表4的68.0和表3的68.0；精确格位见原索引。',
80:'原式为ηpol=hpol/htot×100=[m/(m−1)]/[k/(k−1)]×100。',
83:'原式为eV=Ps/qVac=P1 ln(P2/P1)×1000。',
86:'七份标称标准为GB/T 12785—2014、24674—2021、25409—2010、2816—2014、24489—2025，以及JB/T 11916—2014、JB 10608—2017。',
88:'前一煤气分支系数α=0.95，后一分支α=1.00。',
89:'能耗分值为40、20、10、0；温升及损耗比分值为30、20、10、0。',
92:'专用式为(K1+K4)再乘K5、K10，表A.12小尺寸K4=0.0；A.3计入气氛发生装置总能量，第7.1.2条注3却明确不计供炉气氛发生装置耗电。',
93:'废气行引用GB/T 27946但未列入第2章；固废行写GB/T 15735，而第2章写GB15735。',
94:'表11示例为≤0.2、0.2～1.0、1.0～2.5。',
}
def clean_loc(x):
    s=x['source_location']
    if not isinstance(s,str): raise ValueError(x['id'])
    s=re.sub(r'；(?:表\d+|表\d+～\d+|工作簿表\d+)[^；]*![^；]*','',s)
    s=re.sub(r'PDF(\d+(?:[～~]\d+)?)',r'PDF第\1页',s)
    s=s.replace('/印','（印刷第').replace('§','第')
    s=re.sub(r'（印刷第([\dⅠ]+(?:～\d+)?)',r'（印刷第\1页）',s)
    # Preserve slash-based page groups only in this separate location line, not prose.
    return s.rstrip('。')+'。'

blocks=re.split(r'(?=^#{3,4} (?:EQP-STD-|LOCAL-))',text,flags=re.M)
intro=blocks[0].replace('# 15份标准全部待核事项：Owner阅读入口','# 设备标准待核问题 · 易读版')
intro=intro.replace('### motors（9个）','### 电机（9个）')
intro=intro.replace('逐项完整字段与源SHA保留于 OWNER_ALL_ITEMS.json。','详细坐标和原始证据保留在原索引及 OWNER_ALL_ITEMS.json 中。')
intro += '\n> 本版仅精简表述，不重新判断标准、不新增决定。PDF页码指文件中的物理页；“印刷页”指页面印出的页码。原清单中的建议与未决状态均保留。\n\n'
result=[intro]
for block in blocks[1:]:
    ident=re.search(r'^#{3,4} ([A-Z0-9_-]+)' ,block).group(1)
    fact,doubt,n=edits[ident]
    if n in extras: fact+=' '+extras[n]
    loc=locs.get(n) or clean_loc(items[n])
    block=re.sub(r'^(?:原文与出处|出处/摘录)：[^\n]*',f'原文事实：{fact}\n\n出处：{loc}',block,flags=re.M)
    # Candidate rows combine doubt and impact on the same line: retain impact exactly.
    block=re.sub(r'^疑点：([^\n]*)',lambda m:'疑点：'+doubt+('\n\n影响：'+m.group(1).split('；影响：',1)[1] if '；影响：' in m.group(1) else ''),block,flags=re.M)
    for en,zh in [('motors','电机'),('compressor_boiler','压缩机与锅炉'),('hvac','热工设备'),('fans_submersible','风机、潜水电泵与热处理')]:
        block=re.sub(r'(### )'+en+r'（',r'\1'+zh+'（',block)
        block=block.replace('（'+en+'）','（'+zh+'）')
    result.append(block)
md=''.join(result)
out=p/'设备标准待核问题_易读版.md';out.write_text(md,encoding='utf-8')

# Small local renderer: escaped content, no JavaScript/CDN/font dependencies.
def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return s
body=[];para=[]
def flush():
    if para: body.append('<p>'+inline(' '.join(para))+'</p>');para.clear()
for line in md.splitlines():
    if not line.strip(): flush();continue
    m=re.match(r'^(#{1,4}) (.+)',line)
    if m:
        flush();level=len(m[1]);anchor=re.sub(r'[^\w\-]+','-',m[2]);body.append(f'<h{level} id="{anchor}">{inline(m[2])}</h{level}>')
    elif line.startswith('> '): flush();body.append('<aside>'+inline(line[2:])+'</aside>')
    else: para.append(line)
flush()
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>设备标准待核问题 · 易读版</title><style>
body{margin:0;background:#f4f5f7;color:#202833;font:16px/1.85 "Microsoft YaHei",system-ui,sans-serif}main{max-width:940px;margin:auto;padding:40px 44px 90px;background:white}h1{font-size:29px}h2{margin-top:54px;border-bottom:2px solid #cbd5e1;padding-bottom:12px}h3,h4{font-size:19px;margin-top:44px;padding-top:22px;border-top:1px solid #e2e8f0;overflow-wrap:anywhere}p{margin:12px 0}a{color:#245b8c;overflow-wrap:anywhere}code{font-size:.88em;overflow-wrap:anywhere}aside{background:#eef4fa;padding:14px 18px;border-left:3px solid #647e99}p.source{font-size:13px;color:#647080}p.evidence{font-size:13px;color:#647080}@media(max-width:650px){main{padding:22px 18px}h1{font-size:25px}}@media print{body{background:white}main{max-width:none;padding:0}h3,h4{break-after:avoid}a{color:inherit}}
</style><main>'''+''.join(body)+'</main></html>'
page=page.replace('<p>出处：','<p class="source">出处：').replace('<p>详细证据：','<p class="evidence">详细证据：').replace('<p>原始详细项：','<p class="evidence">原始详细项：')
(p/'设备标准待核问题_易读版.html').write_text(page,encoding='utf-8')
ids=lambda s:re.findall(r'^#{3,4} ((?:EQP-STD-|LOCAL-)[A-Z0-9_-]+)',s,re.M)
assert ids(text)==ids(md)
assert len(ids(md))==103
assert len([x for x in ids(md) if x.startswith('EQP-STD-')])==62
assert hashlib.sha256(src.read_bytes()).hexdigest()==before
assert md.count('原文事实：')==103 and md.count('出处：')==103
for a,b in zip(blocks[1:],re.split(r'(?=^#{3,4} (?:EQP-STD-|LOCAL-))',md,flags=re.M)[1:]):
    for label in ['候选：','建议：','证据强度：','证据：','请核：','关联既有编号：']:
        assert re.findall('^'+label+'.*',a,re.M)==re.findall('^'+label+'.*',b,re.M), (label,a[:70])
    assert a.count('影响：')==b.count('影响：')
class Reader(HTMLParser):
    def __init__(self): super().__init__();self.data=[]
    def handle_data(self,d):self.data.append(d)
r=Reader();r.feed(page)
assert all(i in ''.join(r.data) for i in ids(md))
assert not re.search(r'<(?:script|link|img)\b',page,re.I)
report={'source_sha256':before,'source_unchanged':True,'review_units':103,'existing_ids':62,'supplementary_units':41,'all_ids_same_order':True,'original_decision_fields_preserved':True,'facts_and_questions_rewritten':103,'html_external_dependencies':0,'html_parsed':True,'visual_browser_check':'NOT_RUN'}
(p/'易读版检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
