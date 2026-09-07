任务：固定活动弹幕 token 并记住桌面工具 token
输入版本：TASK-v1
状态：completed
结论：ACCEPTED
证据：AC-001 PASS：创建活动后数据库已有 `activity_danmaku_settings` 且版本为 1；AC-002 PASS：后端测试确认设置更新前后 token 与 `token_created_at` 不变，既有全量测试通过；AC-003 PASS：既有轮换回归确认新旧 token 差异、旧 token 返回 401、连接断开；AC-004 PASS：桌面端 token 记忆测试确认启动页接收并填充最近 token；AC-005 PASS：桌面端测试确认只保存加密字节、安全存储不可用时不写入且全仓类型检查/构建通过；AC-006 PASS：模块 AGENTS、`MEMORY.md`、`LEARNING.md` 和 `WIKI.md` 已同步。
变更文件：`.codex-tasks/20260902-danmaku-token-memory/` 下任务、交接和测试证据文件，以及代码和项目文档变更。
风险或阻塞：无；真实 Windows 重启人工验证未覆盖，但不影响自动化门禁结论。
下一步：完成任务清理并向用户交付。
