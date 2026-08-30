任务：抽奖名单弹窗化与服务端分页优化
输入版本：TASK-v2；DEVELOPMENT-HANDOFF-v2
状态：completed
结论：后端接口、活动隔离、增量更新回归以及全仓前端类型检查和生产构建均通过。
证据：
- `python -m pytest -q`（工作目录 `apps/backend`）退出状态 0：45 passed，1 个既有弃用警告。
- 新增测试覆盖配置无全量 `entries`、名单总数/分页、用户名/手机号搜索、全部/可抽奖/黑名单/白名单/已停用筛选、未登录访问、跨活动隔离、黑白名单互斥、单行保存和配置保存不清空其他标记。
- `pnpm -r typecheck` 退出状态 0，admin-web、screen-web、user-web 和 danmaku-desktop 全部完成。
- `pnpm -r build` 退出状态 0，四个前端生产构建全部完成。
- `git diff --check` 退出状态 0。
变更文件：`apps/backend/tests/test_lottery.py`；`apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue`；`.codex-tasks/20260828-lottery/TESTING-HANDOFF-v2.md`
风险或阻塞：尚未发现阻断问题；构建输出中的既有警告已记录在开发交接。
下一步：由审核角色复核接口安全、分页语义和前端状态处理。

