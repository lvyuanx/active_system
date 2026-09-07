任务：固定活动弹幕 token 并记住桌面工具 token
输入版本：TASK-v1
状态：completed
结论：活动创建事务现在初始化默认弹幕记录；桌面工具在服务端会话校验和投屏窗口创建成功后，通过 Electron `safeStorage` 保存最近一次 token，并在启动页打开时通过受限 IPC 自动填充。
证据：`apps/backend/app/modules/activities/router.py` 在活动 INSERT 后调用 `ensure_danmaku_record`；`apps/backend/app/modules/danmaku/service.py` 保留版本 1 初始记录和旧活动懒补齐；`apps/danmaku-desktop/src/main.ts` 接入安全存储和 IPC；`apps/danmaku-desktop/src/remembered-token.ts` 只写入加密字节。
变更文件：`apps/backend/app/modules/activities/router.py`、`apps/backend/app/modules/activities/AGENTS.md`、`apps/backend/app/modules/danmaku/service.py`、`apps/danmaku-desktop/src/main.ts`、`apps/danmaku-desktop/src/preload.cts`、`apps/danmaku-desktop/src/remembered-token.ts`、`apps/danmaku-desktop/launcher/index.html`、`apps/danmaku-desktop/launcher/launcher.js`、`apps/danmaku-desktop/package.json`及相关文档。
风险或阻塞：Electron `safeStorage` 不可用时不持久化 token，但仍允许手动启动；未引入明文回退。
下一步：执行后端、桌面端和全仓回归测试。
