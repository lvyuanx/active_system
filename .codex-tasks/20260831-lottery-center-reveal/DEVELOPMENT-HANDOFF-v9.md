任务：移除当前奖品提示文字
输入版本：TASK-v9
状态：completed
结论：已移除顶部奖品区域的 `CURRENT PRIZE` 文案，并清理仅服务于该文案的 `.kicker` 样式；奖品图片、名称、网页标题和错误提示保持不变。
证据：

- `LotteryScreen.vue` 删除 `CURRENT PRIZE` 元素，保留顶部奖品图文和动态 `document.title`。
- `LotteryScreen.css` 删除 `.kicker` 选择器，未改变奖品图片尺寸、布局或抽奖状态样式。
- `test-lottery-globe.mjs` 增加 `CURRENT PRIZE`/`.kicker` 不存在的静态断言。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryScreen.vue`
- `apps/screen-web/src/components/lottery/LotteryScreen.css`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/`

风险或阻塞：无；保留工作区中用户已有的其它代码和媒体变更。
下一步：进入测试、审核和场景验收。
