任务：T3 最终回归测试，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：blocked
结论：功能回归、构建、类型检查、43 文件清单和最终产物检查均通过，但启动器 HTML 第 12 行长度为 133，违反仓库 120 字符行宽门禁，因此未放行。
证据：`python -m pytest -q apps/backend` 为 26 passed；`pnpm build` 与 Electron typecheck 退出 0；NSIS、`app.asar`、内置页面存在；行宽检查唯一失败为 `apps/danmaku-desktop/launcher/index.html:12`。
变更文件：无
风险或阻塞：`LINE_LENGTH_EXCEEDED`。
下一步：仅拆分该 HTML 标记行、重建 NSIS、重新检查最终清单和行宽。
