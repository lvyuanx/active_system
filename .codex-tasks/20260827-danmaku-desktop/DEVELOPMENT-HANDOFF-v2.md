任务：T3 开发修复交接：活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：已修复独立测试发现的 AC-009 恢复缺陷，并额外收紧 token 轮换与 WebSocket 加入房间的竞态。断线补齐
HTTP 失败时，渲染器保留原游标、清空未确认缓冲、关闭当前 WebSocket 并由既有指数退避逻辑重连；下一会话会从原游标完整重试补齐。
证据：本地故障注入将 Electron 覆盖层离线，在断线期间发送“断线期间需要补齐”，恢复网络后覆盖层自动显示该消息；
`python -m pytest -q apps/backend` 通过 26 项，`screen-web` 生产构建和 Electron typecheck 均通过。
变更文件：`apps/screen-web/src/components/realtime/DanmakuOverlay.vue`、`apps/backend/app/modules/danmaku/{service.py,manager.py,router.py,AGENTS.md}`、`apps/backend/tests/test_danmaku.py` 和本任务工作流资料。
风险或阻塞：无实现阻塞。最终仍保留单进程广播限制和 Windows 优先范围；临时验收 SQLite 文件受执行环境删除策略限制，受 `.gitignore` 排除。
下一步：以 `WORKPACKAGE-v2.json` 重跑独立测试、审核和验收门禁。

## 修复详情

- `handleReady` 将补齐 HTTP 结果先保存在局部数组；只有全部分页成功后才按消息 ID 与实时缓冲合并投放。
- 补齐失败时不推进 `lastMessageId`，以 1012 主动关闭当前 WebSocket，触发 `onclose` 的指数退避重连；下一次
  `danmaku.ready` 从断线前游标重新请求，避免永久遗漏。
- token 认证主体携带 `token_version`；manager 保存每个活动的最低有效版本，轮换时更新版本并关闭现有连接。旧版本若
  在轮换与房间加入之间交错，则 `connect` 返回 false，路由发送 unauthorized 并关闭，不能重新进入。

## 新增验证

- `test_danmaku_manager_rejects_old_token_connection_after_rotation` 直接验证旧版本连接在轮换后被拒绝，新版本可进入。
- Chrome DevTools 对真实 Electron 覆盖层注入 `Network.emulateNetworkConditions(offline)`；离线时发送聊天消息，恢复网络后
  2.2 秒内捕获覆盖层 DOM 中的“断线期间需要补齐”。

## 重新执行结果

```text
python -m pytest -q apps/backend             26 passed, 1 warning
pnpm --filter @active/screen-web build        exit 0
pnpm --filter @active/danmaku-desktop typecheck exit 0
```
