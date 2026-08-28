任务：审核 TASK-v1 实现、兼容性、活动隔离和交付完整性。
输入版本：TASK-v1；开发交接为 DEVELOPMENT-HANDOFF-v1；测试交接为 TESTING-HANDOFF-v1。
状态：completed
结论：APPROVED。实现范围与任务单一致，没有新增密码字段或无关业务行为；会话撤销、聊天拦截和活动条件均有对应实现与测试证据。
证据：`apps/backend/app/modules/participants/admin_router.py:45-86` 对所有状态更新使用 `activity_id` 条件；`apps/backend/app/modules/participants/router.py:58-123` 校验会话版本和 active 状态；`apps/backend/app/modules/chat/service.py:105-125` 每次发言重新读取用户状态；`apps/admin-web/src/views/participants/index.vue:65-111` 展示状态并提供操作；全量测试、全仓类型检查和构建均成功。
变更文件：审核未新增生产代码，仅形成审核交接。
风险或阻塞：未发现阻断问题；管理端交互需要真实管理员会话才能进行浏览器点击验证，本次未在浏览器输入密码。
下一步：交由验收阶段按 AC-001 至 AC-007 逐条验收。
