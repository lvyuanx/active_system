任务：实现 TASK-v1 管理端参与者管理。
输入版本：TASK-v1；架构交接为 ARCHITECTURE-v1。
状态：completed
结论：已完成活动参与者管理员 API、状态字段迁移、JWT 会话版本撤销、聊天禁言/停用拦截、管理端页面和用户端停用会话清理。
证据：后端测试 `python -m pytest -q` 通过 36 条；`pnpm -r typecheck` 通过；`pnpm -r build` 通过；`git diff --check` 通过；本地 OpenAPI 已列出 5 条参与者管理员路径。
变更文件：`apps/backend/app/core/database.py`、`apps/backend/app/core/security.py`、`apps/backend/app/api/router.py`、`apps/backend/app/modules/participants/`、`apps/backend/app/modules/chat/`、`apps/backend/app/modules/danmaku/testing.py`、`apps/backend/tests/test_admin_participants.py`、`apps/admin-web/src/`、`apps/user-web/src/views/activity/chat.vue` 及对应模块文档。
风险或阻塞：管理端完整登录后的浏览器点击验收未输入管理员密码；已验证未授权入口加载、OpenAPI 路径、类型检查和生产构建。
下一步：交由测试、审核和验收阶段复核。

## AC 映射

- AC-001：`ActivityParticipantResponse` 与管理端表格展示全部参与者信息。
- AC-002：`ChatMutedError` 阻止消息写入并支持解除禁言。
- AC-003/AC-004：`is_active` 与 `session_version` 贯穿 HTTP、WebSocket 和登录流程。
- AC-005/AC-006：管理员接口的活动条件和增量字段迁移由后端测试覆盖。
- AC-007：管理端路由、侧边栏、确认弹窗、行级加载状态和构建验证已完成。
