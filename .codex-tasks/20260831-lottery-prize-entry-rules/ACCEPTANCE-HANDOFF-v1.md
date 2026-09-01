任务：奖品级黑白名单配置
输入版本：TASK-v1；审核交接：REVIEW-HANDOFF-v1.md
状态：completed
结论：ACCEPTED
证据：AC-001 PASS：同一活动两个奖品的名单状态、摘要和候选用户互不串用，见 `apps/backend/tests/test_lottery_prize_entries.py:23-91`；AC-002 PASS：安全码通过后名单弹窗先选择奖品，搜索、筛选、分页和开关操作均使用当前 `prize_id`，见 `LotteryEntriesDialog.vue:20-323` 和 `client.ts:267-296`；AC-003 PASS：`prepare_lottery_round`、`draw_lottery` 的候选池按当前奖品计算，同时保留停用和跨奖品不重复规则，见 `service.py:311-455`；AC-004 PASS：旧 `lottery_entries` 只迁移一次到已有奖品，迁移后的新奖品默认无标记，见测试 `:96-170`；AC-005 PASS：后端 60 条测试、定向 14 条测试、管理端 typecheck/build、静态结构和 diff 检查均通过。
变更文件：本任务实现文件、测试、模块 AGENTS、README/WIKI/MEMORY/LEARNING 和本任务证据。
风险或阻塞：无阻断项；未进行真实浏览器截图验收，UI 交互依赖已通过的 Vue 类型与生产构建验证。
下一步：记录最终文件清单与哈希，保留既有用户工作树变更并完成任务。
