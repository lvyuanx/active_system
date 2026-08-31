任务：实现抽奖球体动画与开始/停止开奖
输入版本：TASK-v1；架构输入：ARCHITECTURE-v1
状态：completed
结论：完成后端两阶段轮次协议、冻结候选池、提交后广播、幂等停止、配置/名单/重置锁定；完成管理端开始/停止控制和全屏 Canvas 3D 球体大屏。
证据：后端 `apps/backend/tests/test_lottery_round.py` 覆盖开始无中奖、公开字段、冻结用户、配置冲突、ready 恢复、重复停止；screen-web `test-lottery-globe.mjs` 覆盖球面分布、投影目标和 easing；生产代码已通过 compile/typecheck/build。
变更文件：`apps/backend/app/modules/lottery/{models.py,round_state.py,state.py,protocol.py,service.py,router.py,manager.py}`；`apps/admin-web/src/views/lottery/` 和 API 类型；`apps/screen-web/src/components/lottery/`、API 类型、20 个本地头像资源和测试脚本；README、WIKI、MEMORY、LEARNING、模块 AGENTS 文档。
风险或阻塞：轮次和连接房间均为单进程内存；后端重启取消未完成轮次；无当前阻塞。
下一步：交由测试执行全量回归及浏览器开始→滚动→停止→揭晓验收。
