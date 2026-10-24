from pathlib import Path
import hashlib,json,openpyxl
base=Path('docs/standards/gbt36561_2018');out=Path('docs/governance/device_full_acceptance_20261013/fans_submersible');items=[]
for rel in ['data/GBT36561_2018_TABLE_VALUES.xlsx','data/table_values.csv','data/table_values.json','evidence/workbook_coordinates.json','build_data.py','STANDARD_MAPPING.md']:
 p=base/rel;items.append(dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(out/'gbt36561_2018'/'defect_input_hashes.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# GB/T 36561—2018 独立验收：已确认转录缺陷（修复前）

本文件仅报告事实，不修改原映射/工作簿，不批准软件解释。原PDF SHA256 f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37；绝对路径与全部验收起点SHA见../source_manifest.json；本次发现相关文件SHA见defect_input_hashes.json。

|缺陷|原PDF原页图像事实|现有交付错误|准确位置与传播|
|---|---|---|---|
|FS-36561-01|物理8/印刷5，表6注a：距主轴端面300 mm|500 mm|XLSX 正文表值!H90；ID GBT36561-2018-T6-0089；data/table_values.csv:90；data/table_values.json:1242 condition；evidence/workbook_coordinates.json:1506 condition；build_data.py:20。主映射仅概述测点，没有写500，不将其概述误报为相同错字。|
|FS-36561-02|同页表6注b：装上直径>φ300 mm的圆盘|≥φ300 mm|XLSX 正文表值!H91；ID GBT36561-2018-T6-0090；data/table_values.csv:91；data/table_values.json:1256 condition；evidence/workbook_coordinates.json:1523 condition；build_data.py:20。会错误纳入恰好300 mm圆盘。|
|FS-36561-03|物理14/印刷11，表11井式炉950℃、容积0.2～1.0m³，升温时间≤1.0 h|≤1.5 h|XLSX 正文表值!F294；ID GBT36561-2018-T11-0293；data/table_values.csv:294；JSON通过record_id定位（其行4101为ID）；workbook_coordinates.json同ID（行4977为ID）。|

三个问题均为原文明确值/符号与转录不一致，不是标准原文歧义，不需要通过Owner改变标准解释来掩盖。第3项会放宽空炉升温时间阈值；前两项改变试验测量条件。建议原编制者修订同源build_data.py并同步生成CSV/JSON/XLSX与证据清单，修复后由独立验收按新SHA复验；当前GB/T36561映射验收为FAIL。

图像证据：table6_note_zoom.png、table11_zoom.png；全部页图page_01.png～page_26.png已实际打开查看。图片只作本地审计证据，不建议随仓上传原标准页面。
'''
(out/'gbt36561_2018'/'CONFIRMED_FINDINGS.md').write_text(report,encoding='utf-8')
print('written')
