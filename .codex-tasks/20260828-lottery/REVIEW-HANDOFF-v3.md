任务：抽奖奖项与奖品树形编辑
输入版本：TASK-v3；DEVELOPMENT-HANDOFF-v3；TESTING-HANDOFF-v3
状态：completed
结论：APPROVED
证据：
- 页面展示层按 `award_id` 分组，新增奖品只能使用当前奖项 ID，避免平铺下拉框选错归属。
- 表单提交仍遍历平面 `form.awards` 和 `form.prizes`，未改变后端 `LotteryConfigUpdate` 接口或库存约束。
- 删除奖项同步移除其子奖品，减少本地表单提交 invalid_award 的机会；已有中奖记录的约束仍由后端最终拦截。
- 未保存奖品从开奖选择器过滤，消除了 `null` 选项和 Element Plus 控制台警告。
变更文件：`apps/admin-web/src/views/lottery/index.vue`；`apps/admin-web/src/views/lottery/lottery.css`
风险或阻塞：无。
下一步：进入逐条用户场景验收。

