任务：抽奖名单摘要移入特殊配置弹窗
输入版本：TASK-v1；审核交接：REVIEW-HANDOFF-v1.md
状态：completed
结论：ACCEPTED
证据：AC-001 PASS：主页面仅保留“抽奖名单”标题和“特殊配置”入口；AC-002 PASS：弹窗展示总人数、可抽奖、黑名单、白名单、已停用统计及规则说明，并绑定 `summary`；AC-003 PASS：未修改弹窗原有搜索、筛选、分页和名单更新逻辑；AC-004 PASS：管理端 typecheck/build、静态结构扫描和 `git diff --check` 均通过。
变更文件：`index.vue`、`LotteryEntriesDialog.vue`、`lottery.css`、相关 AGENTS/README/项目知识和本任务证据。
风险或阻塞：无阻断项；浏览器视觉截图未自动化覆盖。
下一步：清理临时证据并完成最终工作树核对。
