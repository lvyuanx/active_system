任务：验证抽奖球体动画与开始/停止开奖
输入版本：TASK-v1；开发输入：DEVELOPMENT-HANDOFF-v1
状态：completed
结论：所有必需自动化检查通过；后端 57 条测试、大屏既有与球体测试、两端类型检查和两端生产构建均成功。
证据：`python -m pytest -q apps/backend/tests` 退出码 0，`57 passed, 7 warnings`；`python -m compileall -q apps/backend/app apps/backend/tests` 退出码 0；`pnpm --filter @active/screen-web test` 退出码 0，包含 `lottery globe tests passed`；`pnpm --filter @active/admin-web typecheck`、`pnpm --filter @active/screen-web typecheck`、两端 `build` 均退出码 0；`pnpm -r typecheck` 退出码 0；`git diff --check` 退出码 0；新增后端协议测试验证 DB 开始阶段记录数为 0、停止后为 1及公开字段脱敏。
变更文件：补充了 `apps/backend/tests/test_lottery_round.py` 和 `apps/screen-web/scripts/test-lottery-globe.mjs`；开发复核阶段补强大屏历史恢复和本地布局缺失回退。
风险或阻塞：构建保留既有第三方 PURE 注释和管理端大包体积提示，均不影响成功；浏览器运行使用隔离测试数据库和临时服务。
下一步：交由审核检查并发顺序、权限边界、公开字段和范围完整性。
