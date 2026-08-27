任务：T3 独立测试门禁，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：blocked
结论：后端测试、全量构建、Electron 类型检查和安装包检查均通过，但 AC-009 发现恢复缺陷：断线后 WebSocket
恢复成功而 HTTP 补齐暂时失败时，异常被吞掉且连接不再重试，断线期间的消息可能永久遗漏。
证据：`python -m pytest -q apps/backend` 退出 0，25 passed；`pnpm build` 退出 0；Electron typecheck 退出 0；
安装包、`app.asar` 和 `resources/screen-web/index.html` 均存在。缺陷位于当时的
`DanmakuOverlay.handleReady`：补齐 catch 未触发 socket 重连。
变更文件：无
风险或阻塞：`AC-009_RECOVERY_FETCH_FAILURE`。
下一步：开发在补齐失败时保留原游标并关闭 WebSocket 触发重连，补充验证后重新测试。

## AC 结论

- PASS：AC-001 至 AC-008、AC-010。
- FAIL：AC-009，原因是恢复 HTTP 请求失败后没有后续重试。

本交接已触发开发回退；其结论仅作为 v1 失败证据，不用于最终验收。
