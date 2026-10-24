from pathlib import Path
import csv,json,hashlib,openpyxl,collections
out=Path('docs/governance/device_full_acceptance_20261013/fans_submersible')
notes={
'gb19761_2020':['表1全部4×18；ψ/ns合并及六机号边界','表2含续表、65≤ns<80四机号子列、末行同源横杠展开；无插值授权','表3轮毂比与三机号分支，注：子午加速按出口直径','表4五ψ组十ns行，外转子排除条件保持；最后ψ≥1.4无上限'],
'gb28381_2012':['所有5直径列及8比值原区间；b2/D2注、效率%','16物理行；每比值跨两级数行；续表接合；Z=2～3/4～6','高速单级；原不规则数值保留；b2/D2注','高速多级Z=2/3～4；非单调末行68.0保留','节能评价值非等级；续表接合','16物理行及Z/b2/D2注；不得按表2+固定差构造','高速单级节能；5直径分支','高速多级节能；Z及合并比值组'],
'gb28381_2026':['34流量点×三级；m³/h、多变效率%、插值条款','24流量点×三级；m³/h、多变效率%','30流量点×三级；m³/h、整机效率%','32流量点×三级×10压力；m³/min、kPa、kJ/m³；横杠不置零','32流量点×三级×9压力；1m³/min二级40.95/51.05/77.85精度保留','21流量点×三级×14压力；123个总横杠含本表；整数211/262等不补小数'],
'gb32030_2022':['7结构列×3功率×3等级；注1型号，注2基值/容差；跨行合并','4结构列×4功率×3等级；三级续表；98%/96%扬程条件','4结构列×6功率×3等级；非单调5.5→5.0保留；97%/94%条件','4结构列×5功率×3等级；ηgr基值与−Δηgr；横杠','6个等级/功率组合；PN≤100为B，>100为U；表7引用未批准外部数值','2结构×5功率×3等级；一二级合并跨度不同；续表三级−Δηgr']}
heatnotes=['七炉类三个指标，±与准确度分列','真空源行拆两条件，13值','8分支×6项；注a最大值，注b手工/电子相同，注c两补偿独立；周/月不混','两电源组×电压/功率','≤1s与>1s及≤精度','4阈值一致；注a/b两处错误，见发现01/02；注c长500mm棒正确','10设备24寿命，年/h分开','26炉型行×三等；两燃料行kgce/t；所有原规格条件已看','5燃料×4热值端点+α；586异常原样保留','10物理温度行×壳/门盖×三等；超温另定注保留','16条件记录；F294阈值错误；大容积双方商定注；共享端点待解释','10行×三级；续表注1修正目标未定、注2特殊设备商定','9污染物；黑度单位级；其他mg/m³','左右并排各7项；完整14项mg/L','3项×4评分；引用号静默改变见发现04','18评分单元；原6重复、8/9合并2分；全部评价文字/引用已看','3等级下界；中间上界开口；<60非清洁节能','11工艺系数；≤350与>450等条件','3工艺系数','6渗层分支；两渗层族','3单重系数；逆序原区间保留','5工艺系数；≥10/≥20重叠保留','K11/K1两独立维度各3值','15展开记录含δ/横杠/深度文字；气体渗氮合并K1','11工艺材质分支；500℃缺口未补','三车间类别系数','四工艺/温度分支；500℃含等号','14展开分支；高碳/合金钢共1.2源格；去氢大型锻件第一热处理注','6尺寸区间；≤300 K4=0保留']
coverage=[]
for key in notes:
 fn='independent_all_cells.csv' if key=='gb28381_2026' else 'independent_visual_cells.csv'
 records=list(csv.DictReader((out/key/fn).open(encoding='utf-8-sig')));groups=collections.defaultdict(list)
 for r in records:groups[r['table']].append(r)
 pages={'gb19761_2020':['4','4,5','5','6'],'gb28381_2012':['4','4,5','5','6','6,7','7','8','8'],'gb28381_2026':['7,8','8,9','9,10','10,11,12,13','13,14,15,16,17','17,18,19'],'gb32030_2022':['4','4,5','5,6','6','7','7,8']}[key]
 for i,(table,rr) in enumerate(groups.items()):coverage.append(dict(standard=key,table=table,pdf_pages=pages[i],value_slots=len(rr),independent_comparison=sum(r['match']=='True' for r in rr),mismatches=sum(r['match']!='True' for r in rr),method='source_image_rekey' if key!='gb28381_2026' else 'independent_source_grid_all_cells_plus_all_table_pages_visual',conditions_and_notes=notes[key][i]))
rrs=list(csv.DictReader((out/'gbt36561_2018'/'independent_visual_cells.csv').open(encoding='utf-8-sig')));groups=collections.defaultdict(list)
for r in rrs:groups[r['table']].append(r)
for i,(table,rr) in enumerate(groups.items()):coverage.append(dict(standard='gbt36561_2018',table=table,pdf_pages=','.join(sorted({r['pdf_page'] for r in rr},key=int)),value_slots=len(rr),independent_comparison=sum(r['match']=='True' for r in rr),mismatches=sum(r['match']!='True' for r in rr),method='source_image_rekey',conditions_and_notes=heatnotes[i]))
with (out/'TABLE_COVERAGE.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=coverage[0]);wr.writeheader();wr.writerows(coverage)
refs=[]
for p in Path('标准原文/10.潜水电泵相关').glob('*.pdf'):refs.append(dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),independent_fulltext_authenticity_review='NOT_RUN'))
(out/'submersible_reference_hashes.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
print('tables',len(coverage),'slots',sum(x['value_slots'] for x in coverage))
