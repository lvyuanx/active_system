任务：修复 AC-009 首次 WebSocket ready 前断线导致的弹幕遗漏
输入版本：TASK-v1
状态：completed
结论：首次 HTTP session 返回的游标保持为唯一历史基线；每次 `danmaku.ready` 均从当前游标通过 `after_id` 补齐，不再使用 ready 快照静默抬高游标。
证据：`DanmakuOverlay.vue` 已删除首次 ready 的直接游标提升分支，并调用纯函数取得补齐游标；独立回归覆盖 `100 -> 101` 场景，屏幕端测试和 typecheck 均通过。
变更文件：apps/screen-web/src/components/realtime/DanmakuOverlay.vue；apps/screen-web/src/components/realtime/message-order.ts；apps/screen-web/scripts/test-message-order.mjs；apps/screen-web/AGENTS.md；.codex-tasks/20260827-danmaku-desktop/DEVELOPMENT-HANDOFF-v6.md。
风险或阻塞：无开发阻断。未执行全量构建、Electron 或真实 WebSocket 验证，按工作包和任务要求留给下游测试。
下一步：交由 `main-retests` 以 TASK-v1 对 AC-009 执行回归，并继续审核与验收门禁。

## 实现摘要

- 删除首次 `danmaku.ready` 使用服务端 `latest_message_id` 直接提升客户端游标的分支。
- 每次 ready 都从当前 `lastMessageId` 通过 HTTP 消息接口有序补齐；实时 WebSocket 事件继续只触发补齐。
- `getReadyRecoveryAfterId` 明确将 ready 快照与客户端游标分离，避免重连窗口中的消息被跳过。

## 验收标准映射

| AC | 结果 | 证据 |
| --- | --- | --- |
| AC-009 | PASS | 初始游标 `100`、重连 ready 最大 ID `101` 时，补齐请求游标仍为 `100`，合并结果包含 `101`。 |

## 已执行验证

- `pnpm --filter @active/screen-web test`：退出 0，输出 `message-order tests passed`。
- `pnpm --filter @active/screen-web typecheck`：退出 0。
- 受影响代码文件行数均小于 500，最大行宽为 120；`git diff --check` 未报告空白错误。

## 方案偏差与残余风险

未偏离 TASK-v1 或既有“WebSocket 触发、HTTP 有序补齐、去重和失败重试”方案。未在本开发包执行浏览器、真实网络、
Electron、全量构建或打包验证；这些不在本包要求的验证范围内。
