任务：审核 WebSocket 实时抽奖交付
输入版本：TASK-v1；测试输入：TESTING-HANDOFF-v1、BROWSER-EVIDENCE-v1。
状态：completed
结论：APPROVED。实现范围与任务单一致，活动上下文在查询/写入/广播路径明确；管理员与公开端权限分离；开奖和重置使用立即事务并在服务返回后广播；request_id、库存、资格过滤和公开字段裁剪均有代码与测试证据；管理端和大屏端通过独立组件/连接逻辑实现，不修改既有聊天/弹幕协议。
证据：`apps/backend/app/modules/lottery/service.py` 的事务开奖和幂等；`snapshot.py` 的公开裁剪；`router.py` 的角色广播与控制锁；`manager.py` 的房间清理；`apps/screen-web/src/components/lottery/lottery-order.ts` 的 draw_id 去重；`TESTING-HANDOFF-v1.md` 和 `BROWSER-EVIDENCE-v1.md` 的退出状态/DOM/截图证据；全量 `git diff --check` 通过。
变更文件：审核阶段未修改文件。
风险或阻塞：多副本消息总线明确为非目标；构建提示为既有依赖/包体积警告，无阻断问题；未发现 P0/P1/P2 问题。
下一步：按每条 AC 执行最终验收并记录 ACCEPTED/REJECTED。
