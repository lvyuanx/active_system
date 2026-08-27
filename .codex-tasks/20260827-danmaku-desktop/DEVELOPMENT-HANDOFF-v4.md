任务：T3 最终行宽修复交接：活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：已将启动器标题标记拆为多行，消除唯一的 120 字符行宽违规；不改变 DOM 语义、IPC、样式选择器或任何可观察行为。
证据：完整代码行宽扫描无超限；`python -m pytest -q apps/backend` 为 26 passed；`pnpm build`、Electron typecheck 和 `pnpm dist:danmaku:win` 均退出 0。
变更文件：`apps/danmaku-desktop/launcher/index.html` 和工作流资料。
风险或阻塞：无。
下一步：以 `WORKPACKAGE-v4.json` 运行最终最小独立回归，然后进入审核。
