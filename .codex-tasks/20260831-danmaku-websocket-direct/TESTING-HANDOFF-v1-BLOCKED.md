# 测试交接（首次阻断）

任务：
TASK-v1 独立测试：验证 WebSocket 完整弹幕直达链路。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v2`；输入快照 `HEAD-5bc847a-clean-20260831`。

状态：blocked

结论：
目标消息测试通过，但从空 `dist-test` 运行完整 screen-web 测试时暴露旧导入路径；后端全文件测试还触发两项
工作包外媒体删除，测试门禁不得通过。

证据：
- `pnpm --filter @active/screen-web test` 退出 1：实际输出为 `dist-test/realtime/task-scheduler.js`，脚本仍引用
  `dist-test/task-scheduler.js`。
- `pnpm --filter @active/screen-web typecheck` 和 `build` 退出 0。
- `pytest -q apps/backend/tests/test_danmaku.py` 的 7 个断言通过，但 lifespan 默认媒体扫描删除两项 tracked 文件。
- 主 Agent 已从输入快照精确恢复两项文件；未保留越界删除。

变更文件：
测试阶段仅修改 `apps/screen-web/scripts/test-message-order.mjs`；临时生成 `apps/screen-web/dist-test`。

风险或阻塞：
原因码 `OUT_OF_SCOPE_WRITE`；旧导入路径导致干净测试输出失败。审核与验收必须等待开发修复和完整重测。

下一步：
回退开发，修正三个旧编译产物导入路径，并为 `test_danmaku.py` 设置隔离临时 `media_root`；然后从空输出重测。
