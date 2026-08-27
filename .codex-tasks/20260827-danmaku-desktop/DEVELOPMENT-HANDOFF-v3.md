任务：T3 最终格式化交接：活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：在 v2 修复与独立测试通过后，仅对本次新增的管理端、桌面启动器和渲染器样式/模板进行行宽格式整理；未改变接口、数据流、token、WebSocket 或桌面窗口行为。
证据：所有本次修改的代码行均不超过 120 字符；`python -m pytest -q apps/backend` 为 26 passed；`pnpm build`、Electron typecheck 和最终 `pnpm dist:danmaku:win` 均退出 0。
变更文件：`apps/admin-web/src/router/index.ts`、`apps/admin-web/src/views/danmaku/index.vue`、`apps/danmaku-desktop/launcher/styles.css`、`apps/danmaku-desktop/src/main.ts`、`apps/screen-web/src/components/realtime/DanmakuOverlay.vue`。
风险或阻塞：无。
下一步：以 `WORKPACKAGE-v3.json` 执行最终独立回归、审核和验收。
