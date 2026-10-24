from pathlib import Path
import json,csv,hashlib,openpyxl
O=Path(__file__).parent;R=O.parents[3]
s=json.loads((O/'mechanical_summary.json').read_text(encoding='utf8'))
manifest=json.loads((O/'source_manifest.json').read_text(encoding='utf8'))
for p in [R/'STANDARD_ISSUES_REGISTER.md',R/'platform-lock.json']:
 manifest.append({'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for d in ['gb18613_2020','gb30254_2024','gb30253_2024']:
 for fn in ['README.md','BOUNDARY_CANDIDATES.md','BOUNDARY_CASES.md']:
  p=R/'docs/standards'/d/fn
  if p.exists():manifest.append({'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
with (O/'table_coverage.csv').open('w',newline='',encoding='utf-8-sig')as f:
 w=csv.writer(f);w.writerow(['standard','table','pdf_pages','source_rows','efficiency_positions','power_positions','total_compared','mismatch','visual_scope','comparison_method'])
 for x in s:w.writerow([x['standard'],x['table'],','.join(map(str,x['pages'])),x['source_rows'],x['cells']-x['source_rows'],x['source_rows'],x['cells'],x['mismatches'],'全部所列原页已查看；表头/边界/符号视觉核验','独立源PDF格坐标解码与XLSX回读；非逐格手工重录'])
pre='''## 平台预检查与验收边界

2026-10-13。审阅者为独立受托子任务 `/root/device_acceptance_astra/motors`，用户授权 Astra / medium 并行验收。实际仓库 `G:\\Python Project\\EquipEffi`，origin `https://github.com/adgo07/EquipEffi.git`，分支 `codex/six-standard-mappings`，开工 HEAD `d9f711068bde583138a7f3dded6f64dcaa339761`。共享工作区已有修改/未跟踪资产，本审阅只写当前验收目录。父任务报告 fetch 因 TLS 失败，未声称远端同步。根目录预检查见 `../PREFLIGHT_INVENTORY.md`。

locked central SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20` 不变。已验证中央本地 clone origin，读取已合并 `854b544563260f9e79c73e714c85f6589e0f19b3` 的 GUIDE_INDEX、STANDARD_DEVELOPMENT_GUIDE_V0.1、PRODUCT_DELIVERY_POLICY_V1；父任务线上核对指南 blob 一致，见 `../central_guide_online_metadata.json`。**本任务不涉及中央公共 Contract。**相关 Frozen 正文扩读不适用，冲突分类 N/A，无需修改中央 Contract。

适用 MUST：逐项原文定位、范围/分类/输入/单位/表值/公式/修正/判定/边界/不适用/无法判定/输出覆盖、疑点进入根台账、分开标准事实/技术判断/软件决定。MUST NOT：静默纠正标准、将执行者自核当独立原文证据、Stage A 宣布 SUPPORTED、变更锁/Golden/运行时算法。本次未改变既有软件解释。

## 方法与证据边界

阅读全文原 PDF 的全部物理页，渲染后逐页实际查看。以原图确认表头、冷却/电压/极数/转速路由、续表、独立空白、短横线、区间及异常零；另以本目录 `independent_compare.py` 直接从原 PDF 重新提取全部数据格，通过矢量格边界和 CFF 字形轮廓进行解码，与 openpyxl 回读 XLSX 逐格比对。数字字形锚点取已查看 GB30253 PDF7 表头与首两行；相同轮廓才复用数字语义。Unicode/空格/范围符号作显式规范化；效率数字与单独破折号字形区别保留。没有以工作簿值来训练数字映射，没有用生产 JSON/Calculator 作为真值。查阅过执行者提取方法以了解乱码字体，但未执行其提取/核验脚本或以其审计 CSV 为 expected。

这是**全量独立机械逐格比对＋全页视觉核验**，不是声称将每个数字双盲人工重新键录。原页图像全看、数字位置全覆盖；没有未比对表值。相同 PDF 的字形轮廓/矢量层存在共同来源依赖，此限制公开保留。原PDF下载渠道未独立追溯，未声称与官网全文字节相同；官网本轮只核元数据。工作簿使用原文件只读，不重存。所有效率格显示精度格式亦与原源数字的小数位匹配，工作簿公式扫描为零；未另行验证 Excel 应用渲染/打印样式，这不作数值正确性的替代证据。

可重跑：`python docs/governance/device_full_acceptance_20261013/motors/independent_compare.py`。输出 `independent_cell_comparison.csv` 每格含原 PDF 页/分表/行列/bbox、XLSX Sheet/坐标、源值、工作簿值、结果。`table_coverage.csv` 逐表覆盖，`source_manifest.json` 含本次真实绝对路径与 SHA256；这些路径仅为本次执行环境，不是跨机器仓库身份。

'''
metadata={
'18613':('2020','8','2020-05-29','2021-06-01','GB 18613—2012、GB 25958—2010','42E6A7FD8C7E4BD896221D92ABA1709B'),
'30254':('2024','19','2024-08-23','2025-09-01','GB 30254—2013','12889A1BC521618359ED88153B76EEA7'),
'30253':('2024','51','2024-09-29','2025-10-01','GB 30253—2013','F87545B23AF9D0EE22F9CDA964203177')}
notes={
'18613':'''- PDF3 第1章范围六类完整：三相120 W～1000 kW、2/4/6/8极、1000 V以下、50 Hz、N设计/连续/单速/封闭自扇冷；一般单相690 V及以下；电容起动120～3700 W、电容运转120～2200 W、双值电容250～3700 W；风扇专用两类10～1100 W。映射没有把一般电机类型与风扇专用混用。
- 表1以kW，表2～6以W；效率按百分数点值，转速r/min。完整列序经原图与XLSX列头回读一致。表1末行315～1000为区间；0.18/0.20、0.37/0.40等相邻功率未去重。
- PDF3 第4章为功率线性插值，无独立编号公式；映射中的公式明确为数学展开，未造转速插值。BC04中0.15kW四极阈值76.5/72.25/67.35，BC05六极282.5kW二级96.55，独立算术复核一致。
- PDF8 §5.1全面产品性能与§5.2三级最低效率分开。PDF8 §6三相B法、单相/风扇直接法及最高铭牌转速均保留。表6注不可分离驱动须整体效率保留。没有用简单输入输出比值替代三相B法。
- PDF5表3 2200W/4极/1级（表3!C14）是真空白且独立格，不与85.9合并；32处短横线保留。PDF7表6 75W/>1300/3级确为72.0（表6!P15），相邻列为72.8；不是转录错误。
- PDF7～8表6≤500、500～700、700～1000、1000～1300、>1300原区间保留，未静默选择共用端点。阈值等号符合“不低于”，最终容差语义单独待后续接入，未将低于三级等同淘汰。
- 无法选表、缺值、输入错误、范围不适用、系统异常分别描述，输出保留标准/源格/插值/比较口径追溯。未新增产品字段、Domain枚举或Record。

未决请求：R01 原表空白；R02 共用转速端点；R03 GB/T755—2019表21、GB/T5171.1—2014表18及产品标准容差；R04 72.0疑似差异。它们已有本地事实记录，但本轮根台账快照未登记正式编号。
''',
'30254':'''- PDF5 第1章六分支与表1～6一一对应。3(3.3)/6kV与10kV独立，IC01/11/21/31/81W、IC611/616/511/516、IC411三组未混用。总范围200～25000、22400、10000、10000、3150、2800 kW；50Hz三相连续、立卧式及防爆均包含，极数2～12。
- 表1～4按2/4/6/8/10/12极，每极1/2/3级；表5～6仅2/4/6/8极；XLSX列序一致。所有204个功率行保留；三组285处短横线皆为源图可见，不补值。原图数据区没有需要传播的合并效率格。
- 原图确认表1有效末端：2极10000、4极25000、6极18000、8极14000、10极8000、12极5600；表2相应10000/22400/18000/14000/7100/5000；表3的6/8/10/12极末端8000/6300/5000/4000。表4全列至10000，不复制表3缺值。与映射完整一致。
- 单位功率kW、效率%、电压kV，单位换算不靠数值猜测。PDF5 第4章仅额定功率线性插值，无编号公式/无温度海拔修正。200/220kW二极表1中点94.05/93.20/92.40经独立算术复核一致。
- PDF6 第6章“2000kW及以下”用GB/T1032—2023 §12.3 B法，以上§12.8 H法并按推荐值取杂散损耗；恰2000边界无误。GB/T755容差不是任意epsilon，名义比较与完整符合性结论分开；三级限定值表路由正确。
- 无值/无列不被擅改为标准范围排除；缺参数、单位非法、测试口径、系统异常与输出追溯边界完整。未创造正式软件状态或增加运行时公式。

未决请求：请求1 GB/T755容差；请求2 总范围内无表值/无极数列。本轮根台账快照未登记二项正式编号。试验标准及适用修改单全文未取得，作为后续接入证据限制；不能因为试验法引用已列出便声称试验算法已核验。
''',
'30253':'''- PDF5 第1章五类范围保持：低压异步≤1140V、0.55～1000kW、2～16极；高压异步3(3.3)/6/10kV、200～2000kW、4～12极；低压变频0.55～1250kW、45～6000r/min；高压变频≥200kW、45～3000r/min（无总功率上限）；电梯0.55～110kW。一般/防爆、连续工作制保留。
- PDF6 §5与表1～29标题路由全部对照：表1低压异步；2/3/4高压3(3.3)/6kV三种冷却；5/6/7同组10kV；8/9/10低压变频各一级；11～19高压3(3.3)/6kV三冷却×三级；20～28对应10kV；29电梯。效率统一%、功率kW、速度r/min，极数列不当转速列。
- 表1每级2/4/6/8/10/12/16极，表2～7每级4/6/8/10/12极；表8～10的四个速度区间＋十个速度点、表11～28的15个速度点、表29七个速度区间各三级，XLSX列头回读全部一致。
- 表1末功率400～1000、表8～10末功率315～1250、表11～28末功率≥3150，均原图确认且完整对照工作簿，没有删除≥3150行或当外推。表29实际25kW行完整，不错替22。
- PDF7表1 55kW/12极/2级确为0.0（表01!N23），同一行一级/三级为短横线；152个短横线保留，不作0。数据体无需向相邻格传播的合并效率格。0.0原文异常明确列为需确认，未授权判级。
- PDF6 第4章同时允许未列功率/转速线性插值，正文无编号公式。映射将双轴表达标作后续候选，不假称原文有计算顺序/舍入规范。500<n≤600缺锚点、区间不取中心点已明确。独立复算0.65kW二极表1阈值86.7/85.45/82.5；表8在0.55kW、67.5r/min中点60.35；表11在200kW、2250r/min一级93.6，均与候选一致。
- PDF6 §6异步按GB/T22669—2008 §10.2.1 A法额定功率；变频按GB/T32877—2022 §6.2 A法额定转矩＋90%额定转速；电梯按同A法但额定功率。查表坐标仍为额定转速，不误用90%转速；电梯不套通用变频条件。
- 等号、不足三级与淘汰区别、容差引用限制、缺输入/无阈值/系统异常区别、输出追溯均在映射中保留。未增加正式算法或软件支持状态。

未决请求：R1 0.0异常；R2 GB/T755容差；R3 区间速度与插值衔接。本轮根台账快照未登记三项正式编号。外部GB/T755、GB/T22669、GB/T32877全文未纳入本次核验，不将本标准阈值核验说成全套试验程序核验。
'''}
for sid,(year,pages,pub,eff,repl,url)in metadata.items():
 rows=[x for x in s if x['standard']==sid];sub=[x for x in manifest if sid in x['path'] and ('标准原文'in x['path'] or x['path'].endswith('.xlsx') or x['path'].endswith('STANDARD_MAPPING.md'))]
 body=f'# GB {sid}—{year} 独立全量资料核验\n\n结论：**表值全量一致性核验完成；Stage A 出口待补齐问题根登记（NEEDS_INFO）**。未发现已确认数值转录缺陷。此结论不批准软件接入、冻结、SUPPORTED或Phase PASS。未决解释本身不自动使事实映射失败。\n\n'+pre
 body+=f'## 来源身份\n\n原PDF {pages}页已全部查看（包括封面/前言/空白页），发布日期{pub}、实施日期{eff}、替代{repl}与封面一致。[官方登记页面](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno={url})于本轮在线读取显示现行，标准名称/日期一致。此处未用官网其他版全文替换用户源文件。\n\n'
 for item in sub:body+=f'- `{item["path"]}`\n  SHA256 `{item["sha256"]}`。\n'
 body+='\n## 逐表覆盖\n\n|表|原PDF页|功率行|效率位置|含功率总比对格|差异|\n|---|---|---:|---:|---:|---:|\n'
 for x in rows:body+=f'|{x["table"]}|{",".join(map(str,x["pages"]))}|{x["source_rows"]}|{x["cells"]-x["source_rows"]}|{x["cells"]}|{x["mismatches"]}|\n'
 body+='\n所有列、功率点/区间、数字、短横线及独立空白纳入比对，原页表头/续表已看图确认。逐表没有未覆盖数据位置。\n\n## 条款、单位、边界与疑点\n\n'+notes[sid]
 body+='''
## 出口及未覆盖范围

本轮根台账读取快照 SHA256 `f60879e271dcb9a3ae939711add9a63b9d906bc10e0c9a1a6d39c05221caf89e`，对三项标准号均未命中；仅有标准目录下登记请求不满足中央Stage A“疑似问题已全部登记”出口。应由总协调将现有请求转入唯一根台账、分配稳定ID并回链，不需要在事实核验任务中先关闭全部解释。父任务如随后补登记，应再核对相应新快照后更新出口结论，不倒改本报告的历史事实。

未执行软件单元/集成/compileall/smoke/性能测试（not_run，不涉及代码实现）；资料核验41张表检查中本标准各表均0差异。未核验外部试验标准全文、未重新测量电机、未批准容差算法或Numeric Profile、未批准Golden。Knowledge capture：无。
'''
 (O/(f'GB{sid}_{year}_ACCEPTANCE.md')).write_text(body,encoding='utf8')
(O/'README.md').write_text('''# 电动机三项标准独立核验

本轮三项结论均为 **全量表值一致性完成 / Stage A出口待根问题登记（NEEDS_INFO）**。41表、1019功率行、16382源格比对零差异；原PDF全部78页已实际查看。

- [GB18613—2020](GB18613_2020_ACCEPTANCE.md)：6表、1290格。
- [GB30254—2024](GB30254_2024_ACCEPTANCE.md)：6表、3582格。
- [GB30253—2024](GB30253_2024_ACCEPTANCE.md)：29表、11510格。
- [逐表覆盖](table_coverage.csv)、[逐格证据](independent_cell_comparison.csv)、[来源路径/SHA](source_manifest.json)、[机械汇总](mechanical_summary.json)。

方法：独立原PDF矢量格提取＋字形轮廓解码＋XLSX直接回读，结合全部原页视觉核验，不冒称每个数字双盲手工重录。9个本地请求未进入根台账是出口缺口；已保留的未决解释不自动构成映射失败。无映射/工作簿/代码修正，无提交。

PNG仅本地阅图证据，不建议提交源文整页复制；下列脚本可重现数值审计，图像文件可据原PDF重新渲染。原文和被审文件未修改。
''',encoding='utf8')
(O/'.gitignore').write_text('*.png\n*_source_rows.json\ncompare_run.txt\n__pycache__/\n',encoding='utf8')
print('reports written')
