# GB 19577—2024 Stage A 交接

2026-10-13。仅写`docs/standards/gb19577_2024/`；共享分支`codex/six-standard-mappings`，未切换、stage、commit、push。公共入口/台账/BASELINE/HANDOFF/TASK_STATE由总协调维护。

## 已交付

[README](README.md)唯一入口；[主映射](STANDARD_MAPPING.md)覆盖七类设备、10表、15公式、全部条款与试验路由；[配套XLSX](data/GB19577_2024_TABLE_VALUES.xlsx)与decimal词法JSON；源表矩阵、逐格PDF bbox→Excel坐标审计；40项[边界候选](BOUNDARY_CANDIDATES.md)；可复现builder及只读核验脚本。

原件19物理页，正文印刷1～11=PDF7～17。源SHA256 `809170a5c226d35c29a34dc73299c1589e6dc2acfdcb7b0241d0cbb00bfa58d9`。最终XLSX SHA256 `0ebf428916f51a8c1c462149ec4582e916e9cfbefcbfc39435077dcc8011633e`。交付文件哈希见[evidence/FILE_MANIFEST.json](evidence/FILE_MANIFEST.json)。源PDF/扫描页不纳入交付，tmp及node_modules链接被忽略。

## 真实检查

- 8能效表69源行、246能效数值；附录4工况行、15区间+合计；物理分支共源展开78组合。
- 308项原数值对照全匹配，对应305独立源bbox（流量合并源格展开4次）。不是独立验收。
- 最终保存后检查1231 pass、0 fail/error/skip；第一次4项整数显示格式失败已修复，记录不隐藏。
- 10个Sheet已渲染检查，15个公式已与原页图像转写核对；40候选未运行成生产测试。
- 正式unittest/compileall/smoke/性能均not_run，原因纯Stage A不改生产代码；独立逐格验收、外部产品标准完整试算not_run。

## 总协调接手

1. 根台账已登记001～005（比较方向/单位、组合指标、B点温度、圆整、外部引用），本目录没有批准软件解释。第006为前言首次发布年疑似笔误，已查根台账登记EQP-STD-GB19577-006；详见[请求](ISSUE_REGISTRATION_REQUEST.md)。
2. 汇总入口和BASELINE哈希，集中提交本目录应提交文件。不要提交tmp、node_modules、`.inspect.ndjson`、原PDF或整页扫描。
3. 保留未核验范围：外部13份不注日期产品/试验标准全文、蒸汽单位/压力口径、H工况定义、43℃COP来源、完整CSPF试算、独立验收；官方登记验证不等于全文认证。
4. 未决解释解决和映射审核前，不凭本次交付宣布READY_FOR_IMPLEMENTATION、SUPPORTED、冻结或Phase PASS。生产代码/Canonical/数据库/Golden/UI/scope/support均未动。

平台预检查细节在主映射§1；中央ACTIVE读取SHA `854b544563260f9e79c73e714c85f6589e0f19b3`，Frozen Numeric按锁定`ee5feb0cc34dbd99790500fadd0c4c932e202a20`读取。无中央Contract变更。Knowledge capture：无。
