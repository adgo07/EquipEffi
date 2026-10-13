# EquipEffi Phase 0 基线

**基线性质：** Phase 0A 起始不可变事实记录  
**采集时间：** 2026-09-21 23:35:54 +08:00  
**路线：** EquipEffi V2.2  ；**阶段：** Phase 0  
**原则：** 本文件记录真实重跑结果，不复用旧 HANDOFF 的历史数字。

## 版本与 Git

| 项目 | Phase 0A 起始事实 |
|---|---|
| repository | `https://github.com/adgo07/EquipEffi.git` |
| branch | `master` |
| HEAD SHA | `a1643ed38e0b934bbc7562348883b8a8bd4badc5` |
| baseline ref | `pre-v2-rebaseline`，指向上述 commit；未重写历史 |
| HEAD commit | `chore:整理 GitHub 发布目录并迁移到新架构` |
| package | `equipeffi 0.2.1`，来自 `pyproject.toml` |
| runtime entrypoint | `equipeffi.entrypoint:main`；源码兼容入口 `main.py` |
| working tree at start | 4 个未跟踪用户提供文件：V2.2 路线、重构问题 CSV/HTML、架构规范 |
| business code changed in Phase 0 | 否 |

起始工作区的 4 个未跟踪文件是用户本轮输入，未被 tag 纳入；Phase 0 文档只引用其事实，不清理或覆盖它们。

## Python 与依赖

正式基线使用本机完整依赖解释器：

```text
executable: C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe
Python: 3.13.3
PYTHONPATH: src
openpyxl: available
python-docx: available
pytest: not installed
```

补充探测到 `.venv_build\Scripts\python.exe` 为 Python 3.11.15，但只安装了 `pip`、`setuptools`、`tkinterdnd2`，缺 `openpyxl`、`python-docx` 和 `pytest`；该环境结果单独记录，不作为完整依赖基线。

## 质量门禁重跑

| 类别 | command | environment | duration | pass | fail | error | skip | not_run / reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| Legacy Regression | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests -p 'test_*.py'` | Python 3.13.3；`PYTHONPATH=src`；源码工作区；完整依赖 | 139.621 s（PowerShell wall；unittest 内部 138.524 s；2026-09-22 复验） | 880 | 3 | 1 | 3 | 0 |
| Legacy Regression 补充 | 同上，`.venv_build` | Python 3.11.15，缺可选依赖 | 15.021 s | 828 | 2 | 10 | 3 | 0；10 error 主要为依赖缺失 |
| compileall | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m compileall -q src tools tests` | Python 3.13.3；`PYTHONPATH=src`；源码工作区；完整依赖 | 0.219 s（2026-09-22 复验） | 1 | 0 | 0 | 0 | 0 |
| package import | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -c "import equipeffi; print(equipeffi.__file__)"` | Python 3.13.3；`PYTHONPATH=src`；源码工作区；完整依赖 | 0.042 s（2026-09-22 复验） | 1 | 0 | 0 | 0 | 0 |
| pytest | 未执行 | pytest 未安装，项目正式命令为 unittest | — | — | — | — | — | N/A |

Python 3.13 全量 unittest 的 4 个当前缺陷已进入 `QA_BACKLOG.md`：

- `test_v4_reader.V4ReaderTests.test_copied_v4_row_is_read_and_evaluated`：期望 `1级`，实际 `无法判定`。
- `test_v4_writer.V4WriterTests.test_end_to_end_v4_1500_rows_read_evaluate_write_and_reopen`：期望 `1级`，实际 `无法判定`。
- `test_v4_writer.V4WriterTests.test_writer_creates_new_workbook_with_locked_results`：期望 94、92.6、90.4、`1级`，实际结果列为空或 `无法判定`。
- `test_release_audit.ReleaseAuditTests.test_source_and_bundled_wheel_pass_release_audit`：`checks` 缺少 `wheel_pmsm_status`。

这些结果是基线事实，不在 Phase 0A 修复；V4 当前发布表面为 `NOT_SHIPPED`，相关 P0/P1 必须在进入对应发布阶段前关闭或给出证据化决策。

## Core Smoke

以下每项均记录完整命令、环境、耗时和结果；命令均在仓库根目录执行。共享环境为：Windows；Python 3.13.3；解释器 `C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe`；`PYTHONPATH=src`；源码工作区；`openpyxl` 和 `python-docx` 可用。

| smoke | exact command | environment | duration | result / statistics |
|---|---|---|---:|---|
| 公共设备类型 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m equipeffi --list-device-types` | 上述共享环境 | 0.187 s | PASS；15 个公共设备类型 |
| 标准状态 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m equipeffi --status` | 上述共享环境 | 0.185 s | PASS；17 个 manifest pack，均为 `active`；`active` 不等于业务边界已验收 |
| 清水泵示例 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m equipeffi --device-type centrifugal_pump --example` | 上述共享环境 | 0.180 s | PASS；返回 `flow=100`、`head=50` 的示例 |
| 单条评价 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -m equipeffi --device-type centrifugal_pump --json '{"category":"单级单吸清水离心泵","flow":100,"head":50,"speed":2900,"efficiency":80}'` | 上述共享环境 | 0.205 s | PASS；`pump_water`，结论 `1级` |
| 100 条批量评价 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -c "from pathlib import Path; from equipeffi.application.bootstrap import create_application_api; api,_,_=create_application_api(project_root=Path('.')); v={'category':'单级单吸清水离心泵','flow':100,'head':50,'speed':2900,'efficiency':80}; r=api.evaluate_batch({'records':[{'record_id':str(i),'device_type':'pump_water','values':v} for i in range(100)]}); assert len(r)==100; print(len(r))"` | 上述共享环境 | 0.220 s | PASS；返回 100 条，顺序保持 |
| 1500 条批量评价 | `$env:PYTHONPATH='src'; & 'C:\Users\WANGWEI\AppData\Local\Programs\Python\Python313\python.exe' -c "from pathlib import Path; from equipeffi.application.bootstrap import create_application_api; api,_,_=create_application_api(project_root=Path('.')); v={'category':'单级单吸清水离心泵','flow':100,'head':50,'speed':2900,'efficiency':80}; r=api.evaluate_batch({'records':[{'record_id':str(i),'device_type':'pump_water','values':v} for i in range(1500)]}); assert len(r)==1500; print(len(r))"` | 上述共享环境 | 0.783 s | PASS；返回 1500 条，顺序保持 |
| Workspace/Record 保存、恢复、Finalize | N/A；当前 SQLite project repository 仍为占位实现 | N/A | N/A | N/A；明确未测原因：当前能力未实现 |

## 性能现状

测试输入为 `pump_water` 示例：清水泵、流量 100、扬程 50、转速 2900、泵效率 80；日期 `2026-09-21`；Python 3.13.3；源码工作区；单次测量，未设 SLA。

| 操作 | 实测 |
|---|---:|
| Standard Pack 首次加载 | 3.225 ms |
| 同一 Pack 重复读取 | 1.947 ms |
| 单条评价 | 6.342 ms |
| 100 条批量评价 | 70.214 ms |
| 1500 条批量评价 | 983.174 ms |

`JsonStandardRepository.get_pack()` 当前仍会在每次调用中读取并解析 JSON，再返回 deepcopy；实测已登记为 `AUD-040 / QA-P1-007`，Phase 0 只记录，不做缓存重构。

## 关键资产 SHA-256

以下哈希对应 Phase 0A 起始资源；只要标准事实、manifest、模板或淘汰目录发生修改，必须重新记录。

| asset | bytes | SHA-256 |
|---|---:|---|
| `src/equipeffi/standard_manifest.json` | 5471 | `75E63D66D9BB3056109D61084FB1D3957B0623302F6F6D540043AE695FC59E59` |
| `src/equipeffi/resources/standards/blower.json` | 26899 | `9331968CA8E0E8B6D2EDF434FE0BED31D8E687C5048D036329F578493EBB697C` |
| `src/equipeffi/resources/standards/boiler.json` | 8253 | `33921F30A8B59FB836E37C62B9AB7DC790254B020A7A06B8E3FCE75D3CF7B20F` |
| `src/equipeffi/resources/standards/compressor.json` | 698913 | `592AAF0D998C1E914B303D645E437C134D16F2C7131EBBF2577B698626AB06E6` |
| `src/equipeffi/resources/standards/fan.json` | 17847 | `F4439C43C3BFC9AFC06D78A1C4068549B48C26528EC5B7BB2654C8ECA20B05AE` |
| `src/equipeffi/resources/standards/gb30253_2024_pdf_verified_v1.json` | 742369 | `F69C052B46CCD9610896B1E0A58DF0558C9F3AD43A4A04909EF154B4FCBB9250` |
| `src/equipeffi/resources/standards/heat_treatment.json` | 7708 | `127F64CA41E850F2C089B568E8652B0FB46A71DBCB9A27E8802C6289915CD0DA` |
| `src/equipeffi/resources/standards/hvac_thresholds.json` | 91013 | `A5C23D3728B5241C2C2605B066E14447C0E9D9E5B87F11C57D482AFDCBF319A0` |
| `src/equipeffi/resources/standards/motor_hv.json` | 138821 | `CA33032DF1E5A7B83A1814E039249E0315AB4C368452579E900CAABAB3294C9B` |
| `src/equipeffi/resources/standards/motor_lv.json` | 19414 | `183A9B1B9D117C38F7D64ED0FBA5A4C3D03A2D3593E34EF4641A740D89210A95` |
| `src/equipeffi/resources/standards/pump.json` | 11110 | `D1FAB8310AA5ADE7ACCCB379BD347F442D51202E0EE2EEF4CA6E34F5A2F3EA00` |
| `src/equipeffi/resources/standards/submersible.json` | 16048 | `2F23ED3ADD6D86C198CDDB70CFFE38906AF47262DD8B3034FADC4135A894A3FF` |
| `src/equipeffi/resources/standards/transformer.json` | 272693 | `13796785F2EF0BD623EA14F7301EAF739C36388105AEF7B69936218CA4609` |
| `src/equipeffi/resources/elimination_catalog_batches_1_4.json` | 809898 | `B4D8D4A78C9501B47BF0309832C6E6FB9EC69D4A267119278D535A4F1681906C` |
| `src/equipeffi/resources/elimination_catalog_industry_2024.json` | 16103 | `A6E0A440AAE3789E79C667F8C65C36DAA26BCBD3054A471ADCD0E396DA616155` |
| `src/equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx` | 440615 | `8F246ACE6D4E09FB77030B97EAA38A939E41F739E8EB14255E1757E26D087FB2` |
| `src/equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx` | 398096 | `EE9DBE17A06081739CFB8EF0D330CE30B4634CBA5CE29CCD1EAB058D09348810` |
| `src/equipeffi/resources/templates/TEMPLATE_MANIFEST.json` | 4773 | `88CEBE32636A91FC879839A61A61C21E862315E590EE18BB064224C9E14C3714` |
| `docs/2026.9.21 EquipEffi 后续开发总体路线 V2.2.md` | 22998 | `D75426DD7C1D3390B4D1A98FB0A6B12EBCC0E437D368DF9BF0EB10F89DD9B80E` |
| `docs/重构问题清单_20260921.csv` | 12817 | `BB8B37ACF0572C4FFA07D64216598F874536D2CE568F0D93081BE76CEDB44934` |

## Baseline 复验规则

Phase 0B 若未执行，本文件保持起始事实；本次确实未执行 0B。若未来批准 P0 Hotfix，必须追加新的复验段，记录修改前后 HEAD、哈希、测试和结果，不覆盖本节。

## Phase 1 Pump V2 R01–R06 isolated revision（2026-09-27）

此段为 Phase 1 新增快照，不回写或替代上面的 Phase 0 基线。起点为固定提交 `9e413051177fbfa7f1b217de17d344f33176b152`；修订在独立 clean worktree 完成，原工作树不参与复制或验证源代码导入。

| 资产 | 起点 SHA-256 | 修订后候选 SHA-256 | 事实 |
|---|---|---|---|
| `src/equipeffi/resources/standards/pump.json` | `A5B1C43F49C8B6F4785EA3A624DE9AC8FC5AE9FD37608CCB1DB4893229903EF7` | `5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F` | SHA-256 为 Git 提交中的 LF 规范文本字节；仅 T3-08 的 C2 从 `144.33` 改为已授权 `142.33`，逐字段对照没有其他 JSON 值差异；T3-09 C3=`144.33` 保持。 |
| `src/equipeffi/standard_manifest.json` | `D8D80497E7B177F5E244DF1FB0ECD5924737BC050D9E4C7E46412D6D15C2C077` | `5D598B6C028554341CF26B5F5DF241E3538FF06626465C8795F2D1D1ECD9566F` | SHA-256 为 Git 提交中的 LF 规范文本字节；共享 `pump.json` 的 `pump_water` 与 `pump_chemical` 两条 manifest 记录同步到新数据版本；Canonical 数值事实仍以上行逐字段对照为准。 |
| `src/equipeffi/domain/evaluation/evaluators/pump.py` | inherited from base | `615F7EC884CF4EB103FFD74804DFE1A5E2616E0B317AD9C457E16213EDB1FFBB` | SHA-256 为提交中 LF 规范文本字节；泵状态修订；Decimal50、GB 19762—2025 公式、ns_raw 正式分档及总 Q/H 和 suction/stages 换算保持冻结，详见新契约和独立定点测试。 |
| `src/equipeffi/application/services/evaluation_service.py` | inherited from base | `EEF8731E5A162C81441D83BAC4C493D0F9EA5A0014CEC1E44BF5E82535DEB8ED` | SHA-256 为提交中 LF 规范文本字节；应用路由状态修订；清水泵公开准入、化工泵未发布状态在应用边界明确表达。 |

本轮正式命令、环境、用时、统计和全量测试已有失败详见 [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md)。该快照不构成 Golden 批准或 Phase 1 PASS。七个旧 Golden 0.1 文件和其 hash 未改；validator 仅通过版本化来源登记识别一项确切历史 Canonical 指纹，未知指纹仍失败。

## Phase 2 非破坏性工程增量（2026-10-02）

起点 master@78831af1778255e1b19a904e9135d56a9672eaf2。Windows CI 基线来自 run 36970415483 / artifact 11212005437（Python 3.12.10，945 run / 9 fail / 5 error / 3 skip），编号固定于 tests/baselines/windows_full_suite_known.json。本机 Python 3.12.14 最终 975 run / 968 pass / 3 fail / 1 error / 3 skip，比较门禁 PASS；不表示 raw full-suite PASS。

关键资源 Git 规范文本 SHA-256 起点/终点相同；未修改任何 protected resource。

| 资源 | 起点与终点相同 SHA-256 |
|---|---|
| src/equipeffi/domain/evaluation/evaluators/pump.py | 615f7ec884cf4eb103ffd74804dfe1a5e2616e0b317ad9c457e16213edb1ffbb |
| src/equipeffi/resources/standards/pump.json | 5d91f01b1c5f26dc4f364a3156c4e974b159fa1005bd840489c0bc3465c18c0f |
| platform-lock.json | 87a8786f9d630609204b240a496f92bdcbc75904ffc2db71f6f318b596e2c3f4 |
| specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl | e8096d18e4b62a6986222c6e5adec9519fa842ae44860a736d45afa3ae712c8d |
| specs/equipment_efficiency/golden/pump_water_replacement_candidates_v0_1.jsonl | 2600e577b25926263823aa7c42a59b8cd1433b5a6d49c2c0075d14543103ced9 |

18 条批准 Golden、7 条历史 Golden、26 条候选与 3 条 replacement provenance 均保持；完整证据见 PHASE2_EXECUTION_REPORT.md。

## GB 20052—2024 变压器 V2.1 开发基准资产（2026-10-12）

以 `origin/master@a0f502b7169339e55871a65f2a37715081925383` 为本次文档资产变更基线。后续变压器功能开发须共同使用主映射表和人工校对数据工作簿；标准PDF是标准事实最高依据。工作簿SHA与本次已修正输出一致。以下bytes/SHA-256按Git提交中的UTF-8 LF原始blob字节计算（跨Windows/Linux不做CRLF自动转换）；此记录只锁定审阅资产身份，指Owner已批准规则和35表数据项目冻结，但不代表Calculator已验收或SUPPORTED；`D-08 / EQP-STD-GB20052-008` 已获Owner最终确认并`RESOLVED`，变压器仍为 `POST_V1 / NOT_IN_RELEASE_SCOPE`。

| 资产 | bytes | SHA-256 | 用途 / 限定 |
|---|---:|---|---|
| `docs/standards/README.md` | 4114 | `D3A54ED17011A0B7260C320FEAF963DE75FFFF1CEA7A3A9E65AAF7CDF04259B5` | 标准归档入口与当前变压器开发基准索引 |
| `docs/standards/gb20052_v21/GB20052_变压器主映射表_V2.1.md` | 47964 | `5934A9112AEE783B8B0335DB8BBEAD480BDE773C5E4FF365A137E7F9F3C1AE24` | 软件规则、表路由与解释的总依据 |
| `docs/standards/gb20052_v21/GB20052_2024_变压器表1-35人工校对数据工作簿_V2.1.xlsx` | 820355 | `35A499BB5406588CDC300C5019BFFD0DE428D3E08CBA21D076CCC8B6F69F2565` | Owner批准的35表冻结开发数据，历史待核状态保留为过程记录 |
| GB 20052—2024 原文PDF（本地复核件，未随本PR纳入） | — | `862D32069301BB76BCF1477E38BEFDCC32DFB219A409032C41FF374E88863A3F` | 标准事实的最高依据 |

本次只修改映射/交接/基线表述并纳入校对工作簿；未修改运行代码、`transformer.json`、数据库、Golden或标准支持状态。未运行软件测试（本次没有软件行为改动）。


**最终Owner冻结批准（2026-10-12）**：主映射SHA256=`5934A9112AEE783B8B0335DB8BBEAD480BDE773C5E4FF365A137E7F9F3C1AE24`，工作簿SHA256=`35A499BB5406588CDC300C5019BFFD0DE428D3E08CBA21D076CCC8B6F69F2565`，共同形成不可拆分的正式基准，未经Owner具体事先批准不得修改。见`docs/standards/gb20052_v21/GB20052_V21_FROZEN_BASELINE.md`。变压器支持状态未升级。

## 2026-10-13 标准映射归档附录（不改Phase 0历史基线）

仅记录水泵映射正文迁移，哈希按UTF-8/LF；新正文新增历史时期说明并修正共同契约的相对链接，原有业务正文逐字保留。旧路径变为跳转页。

| 迁移路径 | 迁移前正文SHA-256 | 迁移后正文SHA-256 |
|---|---|---|
| `specs/equipment_efficiency/profiles/pump_water.md` → `docs/standards/gb19762_2025/profiles/pump_water.md` | `5ea911f4b3a1dd368f4b5e39384897cd9b11bd209a38ce7f9a205004e91d6403` | `3c05073853c72a7295c13c97c6b02578e1b27bd69cd020e4a8cd5fe9b378d25b` |
| `specs/equipment_efficiency/profiles/pump_chemical.md` → `docs/standards/gb19762_2025/profiles/pump_chemical.md` | `23a7279ce9dbc78d60d1a4b17a44c0e7ff3d97a51be0263c95138a2e76918834` | `a34d044b79dd28640697c8d5a1c8a5096d713ee5df17f53d7a37a5f5caf2b782` |

变压器双文件SHA继续以[原冻结清单](docs/standards/gb20052_v21/GB20052_V21_FROZEN_BASELINE.md)为准，本次核对两项均未变化；不重存XLSX。新入口与验证范围见[整理摘要](docs/governance/STANDARD_ARCHIVE_ORGANIZATION_20261013.md)。

### PR #22 验收修复补记（2026-10-13）

化工泵迁移正文仅加强页首历史措辞说明，`preserved-profile-body`以下未变。UTF-8/LF SHA-256由`a34d044b79dd28640697c8d5a1c8a5096d713ee5df17f53d7a37a5f5caf2b782`更新为`7dfd314574395c3eb59fafc4d2c1e50112b3eb5c44ac205df9388c7b70842991`；上表保留首次迁移时的历史哈希。冻结变压器双文件、Golden及运行时资源未修改。
