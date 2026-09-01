任务：抽奖名单摘要移入特殊配置弹窗
输入版本：TASK-v1；产品交接：PRODUCT-HANDOFF-v1.md
状态：completed
结论：已将主页面参与者数量、五项名单统计和资格规则说明移入 `LotteryEntriesDialog.vue`；主页面仅保留标题及“特殊配置”按钮，弹窗继续复用 `LotteryEntrySummary` 响应式数据。
证据：`apps/admin-web/src/views/lottery/index.vue:145-156` 不再渲染摘要文本，仅保留标题和入口；`apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue:20-29` 渲染五项统计和规则说明；统计样式位于 `LotteryEntriesDialog.vue:309-342`。
变更文件：`apps/admin-web/src/views/lottery/index.vue`、`apps/admin-web/src/views/lottery/LotteryEntriesDialog.vue`、`apps/admin-web/src/views/lottery/lottery.css`、管理端 lottery 文档、README、MEMORY.md、LEARNING.md、WIKI.md。
风险或阻塞：未修改名单 API、搜索筛选分页、黑白名单更新和安全码验证；当前工作树既有变更已保留。
下一步：执行管理端 typecheck/build、静态结构检查和差异检查。
