# 当前 UI 状态盘点

任务：`Qingzhou Desktop UI Guidelines v0.1` 配套 UI Audit  
Execution base：`master@d5d765910b1d80b31300c4c9a70dcbcc2f3d8b29`  
Reference Standard：`GB 19762—2025 离心泵能效限定值及能效等级`  
状态：**AUDIT ONLY / 只盘点，不修改 UI**

> 本文件记录当前默认分支真实 UI 结构，不启动 Phase 2，不修改 Pump evaluator、Canonical、Golden、Excel、数据库、正式 UI 代码或 Frozen Contract。

## 1. 审计依据与边界

重点读取：

- `src/equipeffi/presentation/desktop/main_window.py`
- `src/equipeffi/presentation/desktop/launcher.py`
- 当前 Application facade / metadata projection 的 UI 调用关系。

本次只做源码层 UI Audit。没有把 Tkinter 页面改成 PySide6，也没有把 Web fallback 删除或重构。

## 2. A — 技术栈

当前正式桌面主窗口实际为：**Tkinter / ttk**，不是 PySide6。

主窗口：`EquipmentEfficiencyWindow`。

桌面启动器明确说明：

- 正常路径启动 Tk 窗口；
- Tk/Tcl 不可用时可回退到 Web 窗口；
- 判定内核通过 Application API / `EvaluationFacade` 复用，并不依赖 Tk。

这说明当前 Presentation 技术与中央未来默认 PySide6 方向存在差异，但 Domain/Application 仍具备较好的 Presentation 解耦基础。

本任务只记录该差异，不构成迁移授权。

## 3. B — 当前导航

当前没有 ECQuota/GHGTOOL 那种完整左侧 AppShell 一级导航。

桌面 UI 是一个单窗口工作台：

- 顶部：软件标题、模板下载、V4 工作簿上传/结果导出按钮；
- 左侧：设备类型及公共条件；
- 中间：参数填写；
- 右侧：判定结果。

因此当前不存在“首页 / 标准库 / 新建分析 / 记录 / 参数库 / 设置”的正式产品级导航闭环。

对 Reference Standard 单次判定来说，这种单窗口结构很直接；对完整产品交付来说，标准发现、历史记录、设置等入口仍不足。

## 4. C — 首页

当前没有独立首页。

程序启动后直接进入设备分析窗口。用户可以立即开始分析，这是单任务 MVP 的优点；但无法在首页层完成：

- 最近工作查看；
- 标准发现；
- 最近记录；
- 从业务对象继续工作。

后续是否增加首页应在 Reference Standard UI Design 中结合完整产品闭环决定，本 Audit 不预设最终结构。

## 5. D — 标准库

当前桌面主窗口没有独立标准库页面。

用户主要先选择“设备类型”，标准选择和 Profile 路由由 Application/metadata/标准仓内部完成。普通用户无法通过当前主窗口完成完整的：

- 标准搜索；
- 标准状态查看；
- 适用范围查看；
- 替代关系查看；
- 官方来源查看；
- 从标准详情直接开始分析。

这与当前 Reference Standard Roadmap 中“产品壳仍需继续完善”的状态一致。

## 6. E — Reference Standard：GB 19762—2025 离心泵

### 6.1 页面数量

完成一次离心泵分析的主要工作界面为 **1 个窗口 / 1 个主要工作页面**。

左、中、右三栏同时承担类型选择、输入和结果展示，不需要 Wizard 或多页跳转。

### 6.2 Tab 数量

当前桌面主窗口没有业务 Tab。

因此不存在无真实价值的 Tab 过度拆分问题。

### 6.3 必填输入

字段由 V4 Contract / metadata / Product Profile 动态投影，UI 使用 `display_name` 展示中文业务标签、用 `field_id` 在内部绑定变量。

对离心泵 Reference Standard，核心应包括同一标准规定点下的流量、扬程、转速、泵效率，以及类别、单双吸、级数等必要判定条件；基础设备信息中部分字段为可选。

当前这种 metadata-driven 表单有利于以后减少重复 UI 逻辑。

### 6.4 可自动生成或默认的信息

当前 `as_of` 使用应用层默认日期初始化；部分字段、枚举和约束来自 metadata / V4 Contract。

后续设计应继续区分：

- 用户必须确认的真实设备数据；
- 可以根据设备类型/Profile 自动锁定的值；
- 只为审计保留的内部字段；
- 默认日期及其来源说明。

本 Audit 不改变当前默认值或业务解释。

### 6.5 内部字段泄露

输入表单本身主要展示 `display_name`，`field_id` 只用于内部变量映射，这一点是正向的。

但是判定完成后，右侧普通“判定结果”区域在可读摘要下面直接写入：

```python
json.dumps(self.facade.to_record(result), ensure_ascii=False, indent=2)
```

因此完整序列化记录/内部字段会直接出现在普通用户主结果区。

结论：**存在明确 INTERNAL_LEAK**。

### 6.6 技术信息位置

当前结果区同时包含：

- 醒目的最终能效等级；
- 采用标准；
- 参考能效等级；
- 判定说明；
- 缺失信息；
- 数据质量；
- 完整序列化结果 JSON。

前半部分适合普通用户，最后的完整 JSON 明显应属于高级技术详情/诊断层。

### 6.7 结果醒目程度

右侧结果栏始终可见，最终等级使用较大的粗体标签显示，用户判定后能够直接看到结果。

结论：**YES**。

### 6.8 结果解释

“采用标准 / 判定说明 / 缺失信息 / 数据质量”属于可读业务摘要，这是正向设计。

但摘要下方直接显示原始 JSON，普通层与技术层没有真正分开；“参考能效等级”等信息是否应作为普通主结果，也需要后续产品设计确认。

结论：**PARTIAL**。

### 6.9 标准依据

当前结果摘要可以给出采用标准，业务结果模型中也保留标准引用；但当前桌面窗口没有标准库或专门标准详情页来系统查看适用范围、标准状态、条款/表号和官方来源。

因此依据能力在数据层存在，但产品 UI 呈现仍不完整。

### 6.10 是否适合单页

```text
适合单页：YES
```

离心泵单次分析本身适合“设备基本信息 + 标准必要参数 + 结果 + 依据”在一个主要页面完成。后续即使引入完整 AppShell，也不需要把一次泵分析强拆成多步 Wizard。

## 7. 问题登记

| ID | 类型 | 优先级 | 当前事实 | 后续 UI Design 方向 |
|---|---|---|---|---|
| `EQP-UI-001` | `INTERNAL_LEAK` | P1 | 普通结果区直接显示完整 `to_record()` JSON | JSON/内部字段移至高级技术详情，普通层保留结论和可读依据 |
| `EQP-UI-002` | `INCONSISTENT` | P1 | 当前正式桌面主窗口仍为 Tkinter/ttk，而三软件当前 Windows Desktop 默认方向为 PySide6 | 只作为后续 UI Design/迁移输入，本轮不改技术栈 |
| `EQP-UI-003` | `WORKFLOW` | P1 | 当前缺少首页、标准库、记录等完整产品壳，启动即进入单次设备分析 | Reference Standard UI 优化阶段补齐完整产品任务流，不改变 evaluator |
| `EQP-UI-004` | `USER_NOISE` | P2 | 顶部“V4公共接口”及当前尚未接入的上传/导出入口带有明显实现阶段色彩 | 面向普通用户改成业务语言；未开放能力应清楚标注状态 |
| `EQP-UI-005` | `OVER_DENSE` | P2 | 结果栏同时堆叠业务摘要与完整技术记录，信息层级混合 | 使用渐进展示分开最终结论、业务解释和技术审计信息 |

当前没有发现仅凭源码即可认定为 P0 的 UI 问题。

## 8. 三软件一致性观察

EquipEffi 当前与另外两个软件最大的差异不是颜色或间距，而是产品壳成熟度和 Presentation 技术栈：ECQuota/GHGTOOL 已有 PySide6 导航式桌面壳，EquipEffi 仍是 Tk 单窗口 MVP。

后续应优先统一：

- 产品级导航语义；
- 标准库和记录入口；
- 最终结果层级；
- 高级技术详情入口；
- 中文业务语言。

不应在本次 Audit 中为了“家族一致”重写 Tk 窗口。

## 9. 最终摘要

```text
当前 UI 技术栈：
其他：Tkinter / ttk（Tk 不可用时存在 Web fallback）

Reference Standard：
GB 19762—2025 离心泵能效限定值及能效等级

完成一次业务所需主要页面数：
1 个主要桌面窗口

当前普通 UI 是否暴露内部字段：
YES

当前是否存在明显过度拆页：
NO

当前结果是否足够突出：
YES

当前业务解释是否面向普通用户：
PARTIAL

是否适合优先单页：
YES

P0 数量：
0
P1 数量：
3
P2 数量：
2
P3 数量：
0
```

本盘点完成后停止；不构成 Phase 2 启动或 PySide6 重构授权。