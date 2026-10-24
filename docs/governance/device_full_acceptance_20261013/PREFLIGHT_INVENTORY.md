# 设备类今日映射表清单与定位限制

清单时间：2026-10-13T21:59:39.337602+08:00。范围日：北京时间2026-10-13。
本文件仅固定验收对象与来源，不是标准内容PASS报告；逐文件SHA和完整绝对路径见同目录preflight_inventory.json。

## 平台预检查

- 仓库身份：https://github.com/adgo07/EquipEffi.git；HEAD：d9f711068bde583138a7f3dded6f64dcaa339761。
- 分支：codex/six-standard-mappings；15项新编映射主要未提交，不能只用HEAD复现。
- fetch第一次受FETCH_HEAD写权限限制；已批准重试，但TLS EOF失败。远端新鲜度未确认。
- 本地master比现有origin/master落后46提交；未切换、合并、提交、发布。
- locked central SHA：ee5feb0cc34dbd99790500fadd0c4c932e202a20；本任务不涉及中央公共 Contract。
- 中央clone已核origin；读取本地origin/main 854b544563260f9e79c73e714c85f6589e0f19b3 的GUIDE_INDEX、Standard Development Guide、Product Delivery Policy；中央远端最新性未刷新确认。
- MUST：逐项标准定位、疑点登记、结构/数值分别留痕、事实/技术判断/软件决定区分；MUST NOT：静默修标准、修改冻结双文件/业务代码、自动提升支持状态。
- 模型配置：子任务启动工具接受gpt-6-astra/medium；底层运行遥测不可见。
- 会话定位：list_threads与read_thread均MCP失败；下列15个ID来自仓库协调记录，未冒称正文核实。
- .agents目录实际不存在；无该目录技能可读。使用可用PDF/Spreadsheets技能进行只读验收。

补充：已通过受支持GitHub连接器在线读取中央main的上述三份指南，返回文件blob SHA与本地origin/main对应文件完全一致。三文件的当前适用性已在线核实，元数据见central_guide_online_metadata.json；此检查不改变EquipEffi fetch失败记录。

## 完整版本清单

|标准目录|原编制会话|主映射 / 配套工作簿 / 源PDF|
|---|---|---|
|gb18613_2020|01a1332a-43b0-7c52-85f5-c77a65cb8859|docs/standards/gb18613_2020/STANDARD_MAPPING.md<br>docs/standards/gb18613_2020/data/GB18613_2020_表1-6校对数据_A1.xlsx<br>标准原文/2. GB+18613-2020 电动机能效限定值及能效等级.pdf|
|gb30254_2024|01a1332a-6226-7d73-b5a9-202f6b632183|docs/standards/gb30254_2024/STANDARD_MAPPING.md<br>docs/standards/gb30254_2024/data/GB30254_2024_标准表值.xlsx<br>标准原文/3. GB 30254-2024 高压三相笼型异步电动机能效限定值及能效等级.pdf|
|gb30253_2024|01a1332a-76c9-7e52-a6a5-ff3e509c5214|docs/standards/gb30253_2024/STANDARD_MAPPING.md<br>docs/standards/gb30253_2024/data/GB30253_2024_TABLE_VALUES.xlsx<br>标准原文/4. GB 30253-2024 永磁同步电动机能效限定值及能效等级.pdf|
|gb19153_2019|01a1332a-9377-7211-a591-898516ec7866|docs/standards/gb19153_2019/STANDARD_MAPPING.md<br>docs/standards/gb19153_2019/data/GB19153_2019_标准表值.xlsx<br>标准原文/5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf|
|gb24500_2020|01a1332a-baa5-70d0-bec6-6da564a0bf0c|docs/standards/gb24500_2020/STANDARD_MAPPING.md<br>docs/standards/gb24500_2020/data/GB24500_2020_TABLE_VALUES.xlsx<br>标准原文/11. GB+24500-2020 工业锅炉能效限定值及能效等级.pdf|
|gb29541_2013|01a1332a-e003-7df3-b453-963510f843d8|docs/standards/gb29541_2013/STANDARD_MAPPING.md<br>docs/standards/gb29541_2013/data/GB29541_2013_标准表值.xlsx<br>标准原文/14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.pdf|
|gb19761_2020|01a13341-d23a-7340-b498-573ebe7b84a0|docs/standards/gb19761_2020/STANDARD_MAPPING.md<br>docs/standards/gb19761_2020/data/GB19761_2020_表1-4核对工作簿.xlsx<br>标准原文/8. GB+19761-2020 通风机能效限定值及能效等级.pdf|
|gb28381_2012|01a13341-ede0-7c01-94c9-d8ddcecd0f26|docs/standards/gb28381_2012/STANDARD_MAPPING.md<br>docs/standards/gb28381_2012/data/GB28381_2012_TABLES.xlsx<br>标准原文/9. GB 28381-2012 离心鼓风机能效限定值及节能评价值.pdf|
|gb28381_2026|01a13342-0a50-7e42-8104-70665a4c5d35|docs/standards/gb28381_2026/STANDARD_MAPPING.md<br>docs/standards/gb28381_2026/GB28381_2026_TABLE_VALUES.xlsx<br>标准原文/9. GB+28381-2026 鼓风机能效限定值及能效等级.pdf|
|gb32030_2022|01a13342-2805-7ba3-881c-e7899f66cee5|docs/standards/gb32030_2022/STANDARD_MAPPING.md<br>docs/standards/gb32030_2022/data/GB32030_2022_表值映射.xlsx<br>标准原文/10. GB 32030-2022_潜水电泵能效限定值及能效等级.pdf|
|gbt36561_2018|01a13342-438a-7001-820e-ff5f2fbfc969|docs/standards/gbt36561_2018/STANDARD_MAPPING.md<br>docs/standards/gbt36561_2018/data/GBT36561_2018_TABLE_VALUES.xlsx<br>标准原文/12. GBT+36561-2018 清洁节能热处理装备技术要求及评价体系.pdf|
|gb19577_2024|01a13342-5fb3-73d2-a1d2-c7b00360a341|docs/standards/gb19577_2024/STANDARD_MAPPING.md<br>docs/standards/gb19577_2024/data/GB19577_2024_TABLE_VALUES.xlsx<br>标准原文/13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.pdf|
|gb37479_2019|01a13342-783c-74c0-9590-c9b161326ad1|docs/standards/gb37479_2019/STANDARD_MAPPING.md<br>docs/standards/gb37479_2019/data/GB37479_2019_TABLE_VALUES.xlsx<br>标准原文/15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.pdf|
|gb19576_2019|01a13342-972e-7892-b0bd-357b7cf9d867|docs/standards/gb19576_2019/STANDARD_MAPPING.md<br>docs/standards/gb19576_2019/data/GB19576_2019_TABLE1.xlsx<br>标准原文/16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.pdf|
|gb21454_2021|01a13342-adc3-7b12-b386-b5551c4bd43c|docs/standards/gb21454_2021/STANDARD_MAPPING.md<br>docs/standards/gb21454_2021/data/GB21454_2021_标准表值.xlsx<br>标准原文/17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.pdf|
|gb19762_2025|待定位；会话工具失败|docs/standards/gb19762_2025/STANDARD_MAPPING.md<br>docs/standards/gb19762_2025/profiles/pump_chemical.md<br>docs/standards/gb19762_2025/profiles/pump_water.md<br>标准原文/6 7. GB 19762-2025 离心泵能效限定值及能效等级.pdf|
|gb20052_v21|待定位；会话工具失败|docs/standards/gb20052_v21/GB20052_变压器主映射表_V2.1.md<br>docs/standards/gb20052_v21/GB20052_2024_变压器表1-35人工校对数据工作簿_V2.1.xlsx<br>标准原文/1. GB 20052-2024 电力变压器能效限定值及能效等级.pdf|

共17个标准版本；泵含共同映射和两个Profile分支。变压器gb20052_2024入口指向gb20052_v21双文件，不重复计数。

## 现存证据边界

较早ACCEPTANCE_REPORT仅十套资料729位置抽样，不代表本次完整通过。15项新编原文、泵原文、变压器原文均已定位。本轮逐表结论由Astra独立验收组另行报告。变压器温度换算保持DEFERRED，发现问题仅出示证据，不修改批准决定。
GitHub连接器查询本仓open PR返回空列表（查询时点）；今日PR #21/#22合并由Git历史确认。Knowledge capture：无。
