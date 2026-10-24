# 原编制会话定向修复发送记录

日期：北京时间2026-10-13。用户授权：存在问题的转回负责映射编制的原会话，修复模型Sol中等推理；验收仍Astra中等；不合并。

## 本次唯一实际发送

- 受支持工具：`mcp__codex_app__send_message_to_thread`。
- 目标：`01a13342-438a-7001-820e-ff5f2fbfc969`（GB/T36561—2018原编制会话，来源为仓库协调记录）。
- 显式参数：`model=gpt-6-sol`、`thinking=medium`。
- 首次发送时已确认的问题：表6注a 300 mm误为500 mm，`正文表值!H90`。
- 修复范围：仅`docs/standards/gbt36561_2018/`中相应XLSX/JSON/CSV/证据/CHANGELOG，原页确认后再改；不改根共享台账、其他标准、冻结变压器、业务代码、Golden、产品状态，不切换分支/提交/推送/合并。
- 原始回执：`tool call error: tool call failed for codex_app/send_message_to_thread; Mcp error: -32000: MCP error -32000: Codex app tool request failed`。
- 结论：工具报错，**送达与是否启动均未确认**。不是权限拒绝，不据此声称已完成转发。不重复发送。

发送等待期间又确认H91的严格边界和F294的时间阈值错误，随后确认表15原文GB/T30829.4被H354:H361静默改成GB/T30839.4；未追加调用，避免不确定状态下重复启动。完整问题见`fans_submersible/gbt36561_2018/CONFIRMED_FINDINGS.md`及`defect_input_hashes.json`，均可直接交父会话转发。

## 路由能力与定位边界

当前支持`read_thread`、`list_threads`、`send_message_to_thread`（可显式设置Sol/medium）、`wait_threads`。本会话实际list/read均返回上述通用MCP失败；父会话报告其read返回`post-cutover thread ID has unsupported placement format version 2`，该精确原因是父会话证据，不能冒称本地调用直接返回了同文。

已用`wait_threads`对上述目标、`hostId=local`、`timeoutMs=0`查一次状态，返回`tool call failed for codex_app/wait_threads; MCP -32000 Codex app tool request failed`。状态仍不可确认，未重复发送。不使用内部数据库、隐藏会话存储或其他绕行，不自建替代修复会话。当前电脑工具只支持浏览器，原生桌面控制禁用。

其他标准问题按独立报告交父会话协调。变压器任何实质冻结变更须先取得Owner对具体修订的批准；本轮只列证据。未确认泵/变压器原编制会话ID，不猜测接收者。
