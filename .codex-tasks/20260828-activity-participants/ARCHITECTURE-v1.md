# TASK-v1 架构交接

任务：设计活动参与者管理、禁言/停用状态和会话撤销方案。
输入版本：TASK-v1。
状态：completed
结论：采用活动隔离的管理员 API、`activity_users` 状态字段和 JWT 会话版本；禁言在聊天写入边界拦截，停用在活动身份鉴权和聊天写入边界双重拦截。
证据：`apps/backend/app/core/database.py`、`apps/backend/app/core/security.py`、`apps/backend/app/modules/participants/admin_router.py`、`apps/backend/app/modules/chat/service.py`。
变更文件：架构交接文档；实现变更由开发阶段完成。
风险或阻塞：旧 token 不含会话版本时仅在数据库版本为 0 时兼容；首次停用后旧 token 不会在恢复时重新生效。无需数据删除或密码迁移。
下一步：交由开发实现并由测试验证 AC-001 至 AC-007。

## 方案

- `activity_users.is_active` 默认 1，`is_muted` 默认 0，`session_version` 默认 0；旧数据库由 `init_database` 增量增加字段。
- 新活动用户 token 携带 `activity_user_session_version`；参与者依赖同时校验活动 ID、稳定用户 ID、active 状态和会话版本。
- 管理员停用仅在 active 到 inactive 的边沿递增会话版本，恢复只恢复 active，不降低版本。
- 管理员接口使用 `POST` action 风格，所有查询和更新都包含 `activity_id` 条件，并返回完整参与者状态。
- 聊天历史读取保持既有活动用户鉴权；消息写入每次重新读取 active/muted 状态，避免已有 WebSocket 绕过管理员操作。
- 管理端新增独立参与者页面并复用 `ActivitySidebar`；用户端收到停用产生的未授权聊天错误后清理 token 并停止自动重连。

## 回滚

新增字段保留在 SQLite 表中不会影响旧版本读取；应用回滚后新增状态字段会被旧代码忽略。已递增的会话版本不会自动恢复旧 token，恢复使用需重新登录。
