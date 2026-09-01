任务：抽奖时沉浸式球体与揭晓后恢复
输入版本：TASK-v10；审核输入：REVIEW-HANDOFF-v11
状态：completed
结论：ACCEPTED
证据：

- AC-001 PASS：轮次存在时根节点进入 immersive，外围 UI 和球体 caption 隐藏，球体容器铺满视口并继续执行 rolling/scattering。
- AC-002 PASS：收到匹配中奖结果后进入 selecting/revealed，中心中奖用户放大层继续显示，外围页面保持隐藏。
- AC-003 PASS：revealed 完成后无排队轮次时通过恢复计时清理 `activeRound`，正常页面和最近中奖结果恢复；类型检查、构建和静态断言通过。

变更文件：验收未修改文件。
风险或阻塞：未通过真实管理端点击执行开奖，保留为发布前现场复核项。
下一步：完成任务文档清理并向用户交付。
