任务：在管理端首页增加“打开抽奖大屏”入口
输入版本：TASK-v2
状态：completed
结论：已在每张活动卡片底部增加“打开抽奖大屏”按钮；按钮按当前活动 ID 生成 screen-web 地址并附加 `activity_id` 查询参数，在新标签页打开，保留卡片主体和既有管理操作。
证据：

- `apps/admin-web/src/views/home/index.vue:103-106`：按钮位于带 `@click.stop` 的卡片 footer 中，点击调用 `openLotteryScreen(activity.activity_id)`。
- `apps/admin-web/src/views/home/index.vue:200-203`：大屏基础地址读取 `VITE_SCREEN_WEB_BASE_URL`，默认 `http://localhost:5174`。
- `apps/admin-web/src/views/home/index.vue:270-276`：使用 `URL.searchParams.set("activity_id", activityId)` 生成活动大屏地址，并通过 `window.open(..., "_blank", "noopener,noreferrer")` 打开。
- `.env.example:5-7`：新增大屏地址配置示例。
- `apps/admin-web/src/views/home/AGENTS.md`、`apps/admin-web/AGENTS.md`、`README.md`、`MEMORY.md`、`WIKI.md` 已同步入口行为说明。

变更文件：

- `apps/admin-web/src/views/home/index.vue`
- `apps/admin-web/src/views/home/AGENTS.md`
- `apps/admin-web/AGENTS.md`
- `.env.example`
- `README.md`
- `MEMORY.md`
- `WIKI.md`

风险或阻塞：当前工作树存在此前未提交的用户改动，本次未回退或覆盖无关文件；未在已登录浏览器中执行真实点击验收。
下一步：交由测试、审核和验收阶段复核。
