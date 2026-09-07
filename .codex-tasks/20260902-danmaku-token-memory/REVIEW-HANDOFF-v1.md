任务：固定活动弹幕 token 并记住桌面工具 token
输入版本：TASK-v1
状态：completed
结论：APPROVED
证据：活动创建与弹幕服务继续使用 `activity_id` 隔离；播放设置更新不改变 token 版本；手动轮换接口保持原有失效和断开逻辑；桌面端仅通过受限 IPC 访问 token，`remembered-token.ts` 不依赖 Electron 渲染环境，发布清单已包含新模块；`git diff --check` 无错误。
变更文件：本任务全部变更文件均已按范围检查；新增模块说明已同步到 `apps/backend/app/modules/activities/AGENTS.md`、`apps/backend/app/modules/danmaku/AGENTS.md` 和 `apps/danmaku-desktop/AGENTS.md`。
风险或阻塞：无阻断问题；safeStorage 不可用时的安全降级属于明确设计行为。
下一步：按 AC-001 至 AC-006 进行验收。
