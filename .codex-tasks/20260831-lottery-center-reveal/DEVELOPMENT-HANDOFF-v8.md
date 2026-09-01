任务：移除页面标题文字并设置网页标题
输入版本：TASK-v8
状态：completed
结论：已移除 Header 活动名称和顶部奖品下方默认提示语，活动名称通过快照动态设置浏览器标题；真实错误提示保留在抽奖区域。
证据：

- `LotteryScreen.vue` 移除 `header-activity-name` 和 `subtitle`，新增 `watch` 更新 `document.title`，并保留错误提示回退。
- `LotteryScreen.css` 清理两处无用样式；`index.html` 增加“幸运抽奖”默认 `<title>`。
- `test-lottery-globe.mjs` 覆盖正文文字移除、动态 title 和默认入口 title。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryScreen.vue`
- `apps/screen-web/src/components/lottery/LotteryScreen.css`
- `apps/screen-web/index.html`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/`

风险或阻塞：无；保留工作区中用户已有的其它代码和媒体变更。
下一步：进入测试、审核和场景验收。
