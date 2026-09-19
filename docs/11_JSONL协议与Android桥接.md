# JSON Lines 公共接口协议（v1.0）

该协议是 `ApplicationApi` 的轻量进程适配层，不依赖 Tk、Excel、HTTP 框架或第三方库。Linux 服务、Android 桥接层和桌面调试程序都可以通过标准输入/输出复用同一判定核心。

## 传输约定

- 启动：`python -m equipeffi --jsonl`，或直接运行发布包中的 `.pyz`。
- 每行一个 UTF-8 JSON 请求；空行忽略。
- 每个请求返回一行 JSON，并立即刷新输出。
- `request_id` 为可选客户端关联值，服务端原样回传。
- 单行 JSON 错误只返回错误对象，不终止后续请求。
- 单行请求上限为4 MiB；超限只返回`request_too_large`错误并继续读取后续行。
- 请求可带`protocol_version`，当前仅接受`1.0`；省略该字段兼容早期客户端。
- 发送 `op=quit` 后服务端返回确认并退出；不发送时由输入流结束退出。

发布前可使用 `python tools/smoke_jsonl.py` 检查源码入口；对便携包或原生包分别使用 `--pyz <文件.pyz>`、`--executable <文件.exe>`。追加 `--isolated` 会以 Python `-S` 运行，检查无 site-packages/Tk/第三方依赖的无头环境。该检查会验证协议版本、15类公共接口、普通电动机示例、锁定结果字段契约、PMSM标准包状态及表1/55 kW/12极无数据路径，以及 `quit` 生命周期。

## 请求操作

```json
{"request_id":"s-1","op":"status"}
{"request_id":"s-2","op":"device_types"}
{"request_id":"s-3","op":"schema","device_type":"motor"}
{"request_id":"e-1","op":"evaluate","payload":{"record_id":"M-1","device_type":"motor","values":{"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}}}
{"request_id":"b-1","op":"evaluate_batch","payload":{"records":[]}}
{"request_id":"q-1","op":"quit"}
```

`evaluate_v4` 使用 `payload.sheet` 和 `payload.values`；`evaluate_batch` 使用与公共 API 相同的 `records` 数组。判定结果会保留实际指标、计算指标、查表值、等级比较、淘汰匹配、缺失字段和完整轨迹。`schema`响应还会返回每类设备允许的`allowed_conclusions`、内部`internal_profiles`状态，以及锁定写回列的`result_fields`；客户端无需自行复制鼓风机、热处理设备、热泵热水机的等级差异或PMSM激活门禁。

判定结果中的 `trace_schema_version` 当前为 `1.0`。`trace` 数组每一步均包含稳定的 `step_sequence`（从1开始）和 `rule_id`；评价器仍可在步骤中附加表号、插值端点、阈值、比较方向等专属字段。客户端应按 `rule_id` 识别规则，`step_type` 仅用于中文展示。

## 响应结构

成功响应：

```json
{"protocol_version":"1.0","ok":true,"op":"evaluate","request_id":"e-1","result":{"conclusion":"1级"}}
```

失败响应：

```json
{"protocol_version":"1.0","ok":false,"op":"evaluate","request_id":"e-2","error":{"type":"ApiRequestError","message":"values必须是对象"}}
```

客户端应先调用 `status`，根据标准包状态和淘汰目录能力决定是否展示相应设备或结论。当前 PMSM 包为 `active`，可用于查表判定；表1、55 kW、12极的1～3级效率为标准原文“—”，命中时返回“不在范围”并提供三条无数据查表记录。产业结构调整目录状态为用户提供条目已结构化（未扩展目录全文），这些限制会在状态和判定结果中明确返回。

## Android 桥接建议

Android 外层只需实现行缓冲、JSON 编解码、超时和进程重启；不要复制设备公式或标准表。生产环境建议：

仓库已提供可复用的Kotlin协议客户端：`android/bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt`。它核对`protocol_version`和`request_id`，保留数组结果，将远端错误与“无法判定”分开；可注入进程、socket或测试流。`android/app`提供最小演示界面，可连接socket服务、读取15类设备、提交参数JSON并显示结果；它不复制设备公式或标准表，也不替代目标机上的进程生命周期和安全策略。

1. 使用固定的 `request_id` 关联每个响应，批量请求自行限制单批大小。
2. 将 `protocol_version` 和 `status` 记录到客户端日志，发现版本不兼容时停止写入结果。
3. 将 `error` 与能效结论分开显示；`无法判定`不是传输错误。
4. 不把 JSON Lines 进程当作网络服务暴露，若需远程访问，应在外层增加鉴权和 TLS。
