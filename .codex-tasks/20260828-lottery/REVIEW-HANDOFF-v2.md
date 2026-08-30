任务：抽奖名单弹窗化与服务端分页优化
输入版本：TASK-v2；ARCHITECTURE-v2；DEVELOPMENT-HANDOFF-v2；TESTING-HANDOFF-v2
状态：completed
结论：APPROVED
证据：
- 配置读取已移除完整名单，避免首屏传输和渲染大数组；名单更新接口按 `activity_id` 和 `activity_user_id` 双条件校验。
- 后端名单筛选与开奖候选计算共用 `entry_where`，避免可抽奖统计和实际开奖规则漂移。
- 单行更新在 `BEGIN IMMEDIATE` 内 upsert，且配置保存不再执行名单全量 DELETE/INSERT，未显示用户不会被误删。
- 公开 WebSocket 仍通过 `public_config` 和公开快照输出，名单手机号、黑白名单和停用状态未进入大屏协议。
- 后端 45 条测试、全仓 typecheck/build 和 `git diff --check` 均通过。
变更文件：`apps/backend/app/modules/lottery/repository.py`；`apps/backend/app/modules/lottery/service.py`；`apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue`
风险或阻塞：无阻断问题；关键词包含搜索在极大数据量下仍依赖数据库 LIKE，后续如数据规模显著增长再评估专用搜索索引。
下一步：进入用户场景验收，并核对浏览器弹窗视觉和交互。

