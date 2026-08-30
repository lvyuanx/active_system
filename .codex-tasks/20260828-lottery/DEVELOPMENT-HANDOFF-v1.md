任务：实现 WebSocket 实时抽奖
输入版本：TASK-v1；架构输入：ARCHITECTURE-v1。
状态：completed
结论：完成 lottery 数据模型、活动隔离配置/历史 HTTP、管理员 JWT 首帧 WS、公开只读 WS、BEGIN IMMEDIATE 开奖、request_id 幂等、黑白名单/停用/跨奖品去重、提交后分权限广播、重置和配置更新；完成管理端控制页、大屏滚动揭晓/重连/去重和模块文档。
证据：`apps/backend/app/modules/lottery/models.py`、`repository.py`、`service.py`、`snapshot.py`、`router.py`；`apps/backend/app/core/database.py`；`apps/admin-web/src/views/lottery/`；`apps/screen-web/src/components/lottery/`；后端 lottery 测试 7 条通过。
变更文件：新增 lottery 后端模块及测试；新增管理端 lottery 页面、API 类型、导航；新增大屏组件、协议类型和队列测试；更新参与者注册、模块文档、README、MEMORY、LEARNING、WIKI。
风险或阻塞：连接管理器仍为单进程实现，多副本需要共享消息总线；SQLite 生产迁移仍需保持现有 API 契约。未发现当前实现阻塞。
下一步：交由测试执行后端全量回归、前端 typecheck/build、协议脱敏检查和视觉验收。

实现摘要：

- `lottery_draws` 不保存独立库存扣减值，剩余数量由同事务内的记录计数派生。
- 管理员结果允许手机号/加入时间，大屏结果通过 `LotteryDrawPublic` 和 `public_snapshot` 裁剪为用户名/活动用户 ID。
- 管理端页面将名单黑白名单开关、奖品库存、开奖按钮、历史表和重置确认放在同一活动壳中；大屏按 `draw_id` 基线和队列处理实时结果。
