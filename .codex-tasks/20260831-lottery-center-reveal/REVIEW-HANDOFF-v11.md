任务：抽奖时沉浸式球体与揭晓后恢复
输入版本：TASK-v10；测试输入：TESTING-HANDOFF-v11
状态：completed
结论：APPROVED
证据：

- 沉浸式视图复用既有 `activeRound` 和 globe phase，不新增后端字段，不改变开奖和中奖数据流程。
- 中奖 popup 仍由 `LotteryWinnerReveal` 在 selecting/revealed 阶段负责；恢复计时有重置、错误、新轮次和卸载清理。
- 外围 UI 通过单一根节点状态类隐藏，球体容器改为全屏绝对定位；测试、类型检查、构建和 diff 校验均通过。

变更文件：审核未修改文件。
风险或阻塞：未执行真实管理端开奖；不影响代码路径审核结论。
下一步：按 TASK-v10 逐条执行用户场景验收。
