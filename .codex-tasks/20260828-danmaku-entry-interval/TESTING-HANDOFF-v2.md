任务：依据 TASK-v2 验证多测试用户并发发送和密集弹幕输入效果。
输入版本：TASK-v2；开发交接为 DEVELOPMENT-HANDOFF-v2。
状态：completed
结论：并发发送、真实聊天室/弹幕广播回归、全仓类型检查、构建和 Windows x64 打包均通过。
证据：
- `python -m pytest -q`（工作目录 `apps/backend`）：32 passed；仅有既有 chat router 的 1 条弃用警告。
- `python -m pytest tests/test_danmaku.py tests/test_danmaku_test_config.py -q`：9 passed；集成链路和 100 用户并发 sender 测试通过。
- `python -m pytest tests/test_danmaku_test_config.py::test_danmaku_test_manager_runs_one_sender_per_user -q`：1 passed，确认 100 个用户均产生消息。
- `pnpm --filter @active/screen-web test`：message-order、task-scheduler、danmaku-layout 三组测试通过，原渲染端容量保护保持。
- `node apps/admin-web/scripts/test-danmaku-settings.mjs`：管理端设置和“每个测试用户独立发送”静态断言通过。
- `pnpm -r typecheck`：admin-web、screen-web、user-web、danmaku-desktop 全部通过；`pnpm -r build` 全部成功。
- `pnpm dist:danmaku:win`：退出码 0，生成 NSIS 安装包和 blockmap。
变更文件：测试阶段仅增加/调整测试资产和证据，不修改生产代码绕过失败。
风险或阻塞：真实 100 用户视觉密度受轨道数量、入场间隔和队列最大等待共同限制；“100 人”代表 100 个发送源，不承诺 100 条同时可见。
下一步：交由审核阶段检查并发实现和消息顺序。
