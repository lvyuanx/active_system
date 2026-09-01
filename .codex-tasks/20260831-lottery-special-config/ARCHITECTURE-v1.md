任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；有效产品交接：PRODUCT-HANDOFF-v1.md
状态：completed
结论：在 `Settings` 增加 `lottery_security_code`；lottery 管理路由增加超级用户保护的 `POST /admin/activities/{activity_id}/lottery/security-code/verify`，请求体只接收 `security_code`，后端以常量时间比较并返回 `verified: true`；管理端点击入口后使用 Element Plus 密码式输入框调用该接口，成功后再设置名单弹窗可见。
证据：现有 `request` 已统一附加管理员 Bearer Token；现有名单弹窗由 `entryDialogVisible` 控制，改为统一入口函数即可保持弹窗内部行为不变；`apps/backend/app/core/config.py` 使用 `.env` 加载 Settings。
变更文件：`apps/backend/app/core/config.py`、`apps/backend/app/modules/lottery/models.py`、`apps/backend/app/modules/lottery/service.py`、`apps/backend/app/modules/lottery/router.py`、`apps/backend/tests/test_lottery.py`、`apps/admin-web/src/api/client.ts`、`apps/admin-web/src/views/lottery/index.vue`、`.env.example`、README 与相关 AGENTS/知识/任务证据文件。
风险或阻塞：接口只作为管理端入口的二次验证，不改变既有名单 API 的直接调用兼容性；未配置安全码返回服务未配置错误，不能将默认值设为公开固定密码。
下一步：开发实现后执行后端接口回归和管理端 typecheck/build。
