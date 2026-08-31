任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1；测试输入：TESTING-HANDOFF-v1
状态：completed
结论：APPROVED
证据：审查 `protocol.py` 确认 stopping 广播在开奖线程前、结果仍在事务成功后按角色广播；审查 `LotteryScreen.vue` 确认 drawn 提前到达只缓存并等待 scattered；审查 `LotteryGlobe.vue` 确认 scattering/selecting 不更新 rotation、revealed 隐藏重复 Canvas 中奖者并保留中心卡片；`LotteryGlobe.css` 已移除 `.globe-focus` 及伪元素。
变更文件：后端 lottery 协议和轮次状态、screen-web Canvas 阶段与辅助模块、admin-web 状态同步、类型/测试/文档文件。
风险或阻塞：无阻断问题；大屏连接管理器的跨副本限制属于既有风险，未在本任务扩大范围。
下一步：执行最终验收并停止本轮隔离服务。

审核结论：APPROVED
