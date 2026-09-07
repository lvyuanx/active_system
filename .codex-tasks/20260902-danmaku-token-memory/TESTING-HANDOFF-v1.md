任务：固定活动弹幕 token 并记住桌面工具 token
输入版本：TASK-v1
状态：completed
结论：后端 token 生命周期（创建、设置保存、活动状态切换和数据库重新初始化）、桌面端安全存储读写、IPC 接线、安装包清单和全仓构建均通过验证。
证据：`python -m pytest` 退出状态 0，71 passed；`pnpm typecheck` 退出状态 0；`pnpm --filter @active/danmaku-desktop test` 退出状态 0；`pnpm --filter @active/screen-web test` 退出状态 0；`pnpm --filter @active/admin-web test:danmaku-settings` 退出状态 0；`pnpm build` 退出状态 0；`pnpm --filter @active/danmaku-desktop dist:win` 退出状态 0，发布版 `app.asar` 包含 `dist/remembered-token.js`。
变更文件：`apps/backend/tests/test_danmaku.py`、`apps/danmaku-desktop/scripts/test-token-memory.mjs`。
风险或阻塞：未执行真实 Windows 用户数据目录下的人工重启操作；单元测试已覆盖安全存储可用/不可用和加密字节读写。
下一步：进入只读审核和逐项验收。
