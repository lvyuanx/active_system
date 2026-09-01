任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；有效方案：ARCHITECTURE-v1.md
状态：completed
结论：已完成后端配置项、超级用户安全码校验接口、管理端密码式输入验证和“特殊配置”入口改造；校验成功后才打开原有名单弹窗。
证据：`apps/backend/app/core/config.py` 增加 `lottery_security_code`；`apps/backend/app/modules/lottery/router.py` 增加 `POST /admin/activities/{activity_id}/lottery/security-code/verify`；`apps/admin-web/src/views/lottery/index.vue` 仅在 `verifyLotterySecurityCode` 成功后设置 `entryDialogVisible`；相关测试、文档和 `.env.example` 已同步。
变更文件：`.env.example`、README、管理端 lottery API/页面/模块文档、后端 Settings/lottery 模型/服务/路由/模块文档、`apps/backend/tests/test_lottery.py`、MEMORY.md、LEARNING.md、WIKI.md。
风险或阻塞：当前安全码作为管理员入口的二次验证，不改变既有名单 API；部署必须在后端 `.env` 设置 `LOTTERY_SECURITY_CODE`，未配置时接口返回 503。
下一步：执行测试门禁、审核和逐条验收。
