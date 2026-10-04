# EquipEffi 设备能效分析工具

## 正式产品目标与支持范围（先读这一节）

> **技术资产存在 ≠ 正式支持。** 本仓库包含大量已验证的技术资产（15 类公共设备接口、17 个内部 Profile、16 项标准数据包、Web / JSONL / Android 桥接等）。这些资产的**存在**不代表它们是当前正式支持的产品能力。正式支持范围以 [V1_SCOPE.md](V1_SCOPE.md) 与 [ROADMAP.md](ROADMAP.md) 为唯一权威。

| 层级 | 内容 | 含义 |
|---|---|---|
| **正式产品目标** | **完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`** | Windows V1 首个正式版的完整范围定义 |
| **当前正式支持** | `pump_water`（清水离心泵） | `scope_status = IN_V1`、`support_status = SUPPORTED`；当前唯一已正式发布的评价能力 |
| **V1 必须完成、支持提升候选** | `pump_chemical`（石化离心泵） | `scope_status = IN_V1`；11 条 Golden 已获 Owner 具名批准，Stage D 证据闭环已在 Phase 5 完成并交独立验收。治理状态 `SUPPORT_PROMOTION_CANDIDATE`（统一 Qt 正式路径 `--qt` 运行时取值 `SUPPORTED`）；**独立验收通过前不得写成"正式支持已经生效"** |
| **Legacy / deferred / experimental** | `transformer` 及其他 15 类公共类型相关资产、Web 窗口、Android / JSONL 桥接、Excel 适配器、PMSM 等 | **不代表当前正式支持**。`transformer` 为 `POST_V1`（本轮暂缓，资产保留、不删除不重构）；其余按 `V1_SCOPE.md` 的 `UNDER_REVIEW` / `POST_V1` 状态处理 |

三个维度不得互相冒充：`scope_status`（产品范围）、`support_status`（当前发布能力）、标准开发成熟度（中央 Standard Development Guide Stage A→D）。详见 [V1_SCOPE.md](V1_SCOPE.md) 第 1 节。

交接与继续开发的首选权威入口是 [AGENTS.md](AGENTS.md)、[ROADMAP.md](ROADMAP.md)、[TASK_STATE.md](TASK_STATE.md)、[HANDOFF.md](HANDOFF.md) 和 [PLATFORM_BASELINE.md](PLATFORM_BASELINE.md)（配合 `platform-lock.json`）。历史口径（2026-09-05 及更早）曾把 [后续 Agent 和大模型可直接照做交付清单 v15](docs/27_后续Agent和大模型可直接照做交付清单_v15_20260905.md) 作为交接入口。该手册把 15 类公共接口、17 个内部 profile、逐 profile 任务卡、标准证据卡、固定低 CPU 命令、结果契约和 HANDOFF 模板拆成可直接执行的步骤；该手册与 v14 及更早的编号清单现统一标记为 `HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK`，只保留历史事实价值。当前权威来源：`ROADMAP.md`、`HANDOFF.md`、`TASK_STATE.md`、`AGENTS.md`。

以下编号交付清单为历史基线（`HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK`），仅作历史证据保留：[多 Agent 可直接照做交付清单 v14（执行手册）](docs/26_多Agent可直接照做交付清单_v14_执行手册_20260905.md)、[后续 Agent / 大模型可直接执行交付清单 v13](docs/25_后续Agent可直接执行交付清单_v13_20260905.md)、[后续 Agent 直接照做交付清单 v12](docs/24_后续Agent直接照做交付清单_v12_20260904.md)、[多 Agent 详细交付清单 v11（可直接派发）](docs/23_多Agent详细交付清单_v10_可直接照做_20260901.md)（文件名保留 v10 以兼容既有链接）、[多 Agent 详细交付清单 v9（可直接照做）](docs/22_多Agent详细交付清单_v9_可直接照做_20260901.md)、[多 Agent 逐项交付清单 v8（可直接执行）](docs/21_多Agent逐项交付清单_v8_可直接执行_20260901.md) 和 [交接执行清单 v7（可直接照做）](docs/20_交接执行清单_v7_可直接照做_20260901.md)。历史实现记录仍见 `HANDOFF_20260831.md`。

当前版本提供15类V4公共设备接口、可追溯的标准查表/计算判定、第一至第四批机电淘汰目录及用户提供的2024年产业目录条目匹配，以及Tk桌面窗口。若目标Python缺少可用Tcl/Tk运行库，`--gui`会自动降级为同一API的Web窗口。Excel读写位于独立适配器层，核心判定不依赖Excel。

> 上段描述的是**仓库现有技术资产**，不等于**正式支持范围**。正式产品目标、当前正式支持、V1 未发布项与 Legacy/deferred 资产的分层见本文开头「正式产品目标与支持范围」一节。

结果契约版本由领域对象统一携带：当前`trace_schema_version`为`1.0`，核心服务、批量/API、Web和JSONL输出保持一致。

本地发布构建产物默认位于`outputs/`，该目录已加入`.gitignore`，不会随源码上传。发布时可生成wheel、便携`.pyz`、便携ZIP和发布审计；PMSM 29张表已完成复核，Excel导入/回写暂不启用，仅保留接口。

核心批量接口已做1,500条输入抽样（约1.2秒，含结果序列化）；该数据不代表Excel读写性能，Excel适配器仍按后续阶段单独验收。

## 运行

在源码目录：

```powershell
$env:PYTHONPATH = "src"
python -m equipeffi --list-device-types
python -m equipeffi --status
python -m equipeffi --device-type motor --json '{"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}'
python -m equipeffi --gui
# 无Tk时使用纯标准库浏览器窗口
python -m equipeffi --web --open-browser
```

源码兼容入口也支持 `python main.py --status`，返回相同的标准包和目录能力快照。

也可以构建并安装wheel：

```powershell
python tools/build_release.py --output-dir dist
# 可显式指定本次审计使用的人工校对册；不指定时自动优先寻找最新交付目录
python tools/build_release.py --output-dir dist --review-book outputs/final_20260828_web_latest/设备能效标准数据_人工校对版.xlsx
python -m pip install dist/equipeffi-0.2.1-py3-none-any.whl
equipeffi --gui
```

发布目录中的`发布审计_20260830_portable_provenance_v12.json`可复核标准激活、模板、校对册、目录和便携包状态；`15类公共接口示例判定摘要_20260830.md`提供一份人可读的15类示例结果；不需要重新构建即可运行该目录内的`.pyz`进行隔离烟测。

同目录的`发布审计_20260830_with_native.json`还核对了当前源码构建的Windows原生ZIP；原生包为CLI+Web回退模式（80个成员），当前可执行文件未宣称Tk GUI能力。

同目录的`equipeffi-20260831.wxs`和`msi-dry-run-20260831.json`是基于该原生包生成的WiX v4安装源；本机未安装WiX，因此没有生成伪MSI。

发布构建使用项目级非阻塞互斥锁，并默认在180秒后终止超时的wheel构建；
若已有构建正在运行会立即提示，不会并发启动多个高CPU进程。可用
`--timeout`调整单次wheel构建上限，例如 `--timeout 60`。

构建不依赖网络的跨平台便携包（不覆盖wheel）：

```powershell
python tools/build_portable_bundle.py --wheel outputs/final_20260828_web_latest/equipeffi-0.2.1-py3-none-any.whl --output outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.zip
```

生成无需安装 wheel 的跨平台 `.pyz`：

```powershell
python tools/build_zipapp.py --output outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz
python outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz --status
```

批量JSON请求使用与单条请求相同的`device_type`和`values`字段，返回数组并保持输入顺序：

```powershell
equipeffi --batch-json '{"records":[{"record_id":"B-1","device_type":"motor","values":{"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}}]}'
```

Linux服务或Android桥接可使用无框架 JSON Lines 入口：`python -m equipeffi --jsonl`。
每行请求形如`{"op":"evaluate","payload":{"device_type":"motor","values":{...}}}`，
响应严格为一行JSON，带有`protocol_version`和可选的`request_id`；支持`status`、
`device_types`、`schema`、`evaluate`、`evaluate_v4`、`evaluate_batch`和`quit`，单行错误不会终止后续请求。
协议细节见[JSONL协议与Android桥接说明](docs/11_JSONL协议与Android桥接.md)。

需要固定判定基准日期时，在单条或批量入口增加 `--as-of YYYY-MM-DD`；批量JSON也可在请求对象或单条记录中提供 `as_of`。

## 界面与模板

桌面窗口可选择设备类型、按V4契约填写参数、选择淘汰目录口径并查看完整结果。窗口中的“下载空白模板”“上传V4工作簿”“导出判定结果”通过回调端口连接Excel适配器；当前仅启用模板下载和接口提示，Excel导入/回写暂不执行，也没有环境变量旁路。核心API和移动端不需要导入Tk或Excel库。

即使V4工作簿契约暂不可读，公共API和桌面回退表单也会复用同一套数值边界提示（效率1～100、级数/极数正整数、外静压非负、锅炉冷凝效率动态上限）；这些提示不替代最终的服务端质量检查。

效率类字段统一按百分数本值填写：98%填写`98`；`0.98`和大于`100`的值会被V4输入质量检查拒绝。`效率容差Δη`属于标准容差值，不套用效率百分数范围。

`--web`提供一个不依赖Tk/第三方Web框架的浏览器窗口：启动后在浏览器中选择15类设备、按字段契约输入出厂设计/额定/铭牌值并查看完整判定轨迹。它与Tk窗口共享`ApplicationApi`和判定内核，适合作为Linux或后续移动端的可替换展示层；HTTP层同时提供单条`/api/evaluate`和批量`/api/evaluate-batch`，`/api/template`可下载内置空白模板，`/api/template/upload`通过`TemplateTransferPort`预留给Excel适配器接入，默认不会解析或写回工作簿。

内置V4模板通过`importlib.resources`加载，下载时复制到用户选择的位置，不覆盖内置模板。永磁同步电机GB 30253-2024标准包已完成29张表逐表人工复核，当前状态为`active`，可用于正式查表与判定。
窗口结果标题与V4字段保持一致：鼓风机显示“能效结论”，热处理设备显示“评价等级”，其余设备显示“能效等级”。

标准数据人工校对已完成：全量校对册包含61958条记录，均为“正确”，17个内部标准包均已激活。全量激活版位于`outputs/final_20260830_all_verified/`；原始校对册不被覆盖。
其中表1、55 kW、12极的1级、2级、3级效率经用户确认均为标准原文“—”（无数据）；机器数据保留为空、不参与插值或比较，命中时按“不在范围”返回，并保留三条查表轨迹。
校对册验收还会逐项比对16个锁定标准字段与当前机器数据包；允许Excel的空白/数值类型转换，但会拒绝真实标准字段漂移。
2024年产业目录目前仅接入用户明确提供的受控设备条目，尚非全文；采用产业目录口径时，明确命中仍判定“淘汰”，条件不足或未覆盖均返回“无法判定”，不把未命中解释为未淘汰。
目录状态中的来源条目总数为413（第一至第四批402条，产业目录11项原文）；产业目录原文拆分为13条受控规则，状态另以`industry_resource_rule_count`显示；“已启用”数量仍只统计可直接匹配的124条规则。

GB 19577-2024的表1/表2为二选一指标体系；表2的COPc主指标达到3级时，还需提供并达到同一行的`CSPF/IPLV/ACCOP`三级固定门槛。主指标已达到1级或2级时，该仅适用于3级的辅助值可以不填；判定结果会保留门槛查表和比较记录。

V4自动备注还会按设备类别复核动态指标名称和值：热泵和冷水机组表1/表2的主、辅助指标，多联机容量≤14 kW时的EERmin，以及低温多联机的HSPF、COP(-12℃)、COP(-20℃)。名称错误、额外指标或缺少适用设计值只产生数据质量提示，不改写输入，也不替代标准评价器的查表结论。

## 验收

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p 'test_*.py'
python tools/audit_release.py --wheel dist/equipeffi-0.2.1-py3-none-any.whl
# 审计还会检查产业目录受控规则ID的缺失、多余和重复；有原始PDF时再加 --industry-source-pdf
# 便携包构建后校验清单和所有成员SHA-256：
python tools/validate_portable_bundle.py outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.zip
# JSONL桥接最小协议回归（可替换为.pyz或原生可执行文件）：
python tools/smoke_jsonl.py
python tools/smoke_jsonl.py --pyz outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz
python tools/smoke_jsonl.py --pyz outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz --isolated
# 生成PMSM逐表人工复核清单（只读，供追溯）：
python tools/build_pmsm_review_queue.py --output outputs/final_20260828_web_latest/GB30253-2024_PMSM人工复核清单.md
# 生成29张PMSM标准表涉及的PDF页面复核图像及索引（仅用于追溯核对）
python tools/render_pmsm_review_pages.py --output-dir outputs/pmsm-pdf-review
# 审计17个标准包的data_id和记录级PDF页码覆盖（只读，不猜测页码）
python tools/audit_standard_provenance.py --source-dir "<标准PDF目录>" --markdown outputs/standard-provenance.md
# 为缺少标识的机器标准记录补录稳定内部data_id；默认只预览，写回需显式--apply
python tools/enrich_standard_data_ids.py
python tools/enrich_standard_data_ids.py --apply
# 若来源DOCX可访问，可把来源核对并入发布审计：
python tools/audit_release.py --wheel dist/equipeffi-0.2.1-py3-none-any.whl --elimination-source-dir "<第一至第四批DOCX目录>" --output outputs/release-audit.json
# 发布审计也可追加标准PDF目录，来源覆盖只作为非阻断告警
python tools/audit_release.py --standard-source-dir "<标准PDF目录>"
# 核对第一至第四批DOCX来源与机器目录（只读）
python tools/verify_elimination_sources.py --source-dir "<第一至第四批DOCX目录>"
# PMSM标准包已激活；如重建新版本，仍须用独立输入/输出文件完成逐表复核后再激活
python tools/activate_gb30253_pack.py normalized.json review.json active.json
# 也可从人可读校对册导出review.json（要求PMSM全部记录为“正确”）
python tools/export_pmsm_review_json.py outputs/final_20260828_web_latest/设备能效标准数据_人工校对版.xlsx review.json --reviewer 张三 --review-date 2026-08-27
# 标准校对册要作为可激活发布物时，再增加：
python tools/validate_human_review_book.py outputs/final_20260828_web_latest/设备能效标准数据_人工校对版.xlsx --require-activation
# 或在正式构建时使用：
python tools/build_release.py --require-activation
# 正式构建会在输出目录自动同步人工校对册，并保存“发布审计_<目录名>.json”
# 用户确认全部标准已校对后，生成不覆盖原文件的规范化副本：
python tools/confirm_standard_review_book.py input.xlsx outputs/all-verified/设备能效标准数据_人工校对版.xlsx --reviewer "用户确认" --review-date 2026-08-30 --confirmation outputs/all-verified/全量标准人工复核确认_20260830.json
# 原生Windows/Linux目标机可用PyInstaller时，生成可复现原生ZIP：
python tools/build_native.py --output-dir outputs/native --zip-output outputs/native/equipeffi-native.zip --report outputs/native/native-build.json
# 具备WiX v4时，从已验收的onedir目录生成正式MSI；当前机可先预览WXS，不会伪造MSI
python tools/build_msi.py --native-dir outputs/native/dist/equipeffi --output outputs/native/equipeffi.msi --dry-run
```

判定结果中的`actual_metrics`、`calculated_metrics`、`limits`、`lookups`、`comparisons`和`trace`均可供报告、Excel或其他客户端使用；原始输入不会被自动改写。
