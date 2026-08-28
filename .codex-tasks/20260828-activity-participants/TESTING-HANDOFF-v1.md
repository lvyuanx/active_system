任务：验证 TASK-v1 参与者管理功能。
输入版本：TASK-v1；开发交接为 DEVELOPMENT-HANDOFF-v1。
状态：completed
结论：AC-001 至 AC-007 的后端行为和前端构建门禁通过；未发现阻断问题。
证据：`apps/backend/tests/test_admin_participants.py` 4 条新增测试通过；后端全量 `36 passed, 1 warning`；`pnpm -r typecheck` 四个前端项目通过；`pnpm -r build` 四个前端项目通过；`pnpm --filter @active/admin-web test:danmaku-settings` 通过；本地 OpenAPI 返回 5 条 participants 路径。
变更文件：测试资产为 `apps/backend/tests/test_admin_participants.py`；测试阶段未修改生产代码。
风险或阻塞：构建保留既有 Vite/Rollup 大 chunk 警告和 PyJWT 依赖弃用警告，不影响退出状态或本任务行为。
下一步：交由审核阶段检查实现边界、兼容性和文档完整性。

## 用例映射

- AC-001/AC-005：列表、超级管理员权限、无效活动、无效用户和跨活动 ID。
- AC-002：禁言用户仍可登录/读取，WebSocket 发言返回 `muted`，解除后恢复。
- AC-003：停用后 `/me`、聊天历史、登录、已有 WebSocket 发送和新 WebSocket 鉴权均拒绝。
- AC-004：恢复后旧 token 仍拒绝，新登录 token 的会话版本为 1 且可用。
- AC-006：旧表初始化增加三个字段并得到 `(1, 0, 0)` 默认值；旧 token 在首次停用前保持兼容。
- AC-007：管理端类型检查、生产构建、路由入口加载和已有前端静态回归通过。
