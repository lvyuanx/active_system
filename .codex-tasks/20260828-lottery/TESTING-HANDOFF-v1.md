任务：验证 WebSocket 实时抽奖
输入版本：TASK-v1；开发输入：DEVELOPMENT-HANDOFF-v1。
状态：completed
结论：所有必需自动化验收场景通过；后端全量 43 条测试通过，大屏协议/调度测试通过，管理端与大屏端类型检查通过，完整 workspace 构建通过。
证据：执行 `python -m pytest -q`，退出状态 0，`43 passed, 1 warning`；执行 `pnpm --filter @active/screen-web test`，退出状态 0，`message-order`、`task-scheduler`、`danmaku layout`、`lottery order` 均通过；执行 `pnpm -r typecheck` 和 `pnpm -r build`，退出状态 0；执行 `git diff --check`，退出状态 0。
变更文件：测试资产为 `apps/backend/tests/test_lottery.py` 和 `apps/screen-web/scripts/test-lottery-order.mjs`；测试阶段未修改生产代码。
风险或阻塞：构建保留既有第三方 `@vueuse/core` PURE 注释提示和管理端大包体积提示，均非失败；浏览器视觉验证使用隔离测试数据库，未触碰项目默认数据库。
下一步：交由审核检查范围、权限边界、事务顺序和文档完整性。

用例映射：

- AC-001/002/003：配置/历史 HTTP、管理员鉴权、公开 ready 脱敏。
- AC-004/005/006/007：管理员与大屏实时开奖、BEGIN IMMEDIATE 并发、request_id 幂等、资格过滤。
- AC-008/009/010/012：错误不广播、重置、安全配置广播、ping/pong 和活动隔离。
- AC-011/013/014/015：ready 恢复与队列去重、管理端控制页、大屏视觉和既有回归构建。
