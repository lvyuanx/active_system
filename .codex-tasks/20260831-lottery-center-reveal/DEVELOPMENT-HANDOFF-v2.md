任务：移除最终中奖卡片
输入版本：TASK-v2
状态：completed
结论：已删除 revealed 阶段的矩形中奖卡片 DOM 和样式，让中心用户放大层从 selecting 持续展示到 revealed；停止、打散、开奖和 WebSocket 流程未改变。
证据：

- `LotteryWinnerReveal.vue:2-14` 将中心层条件扩展为 selecting/revealed，已移除 `data-winner-card` 和 `.globe-winner` 标记。
- `LotteryWinnerReveal.css` 已移除卡片背景、边框、阴影、卡片图片样式和 `globe-winner-in` 动画，仅保留中心头像/姓名放大效果。
- `test-lottery-globe.mjs` 断言中心层持续到 revealed，并断言卡片 DOM/CSS 不存在。
- `pnpm --filter @active/screen-web test`、`typecheck`、`build`、`git diff --check` 均退出码 0。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryWinnerReveal.vue`
- `apps/screen-web/src/components/lottery/LotteryWinnerReveal.css`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`、`LEARNING.md`、`WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/TASK-v2.md`

风险或阻塞：未改变中心放大层的时序；真实目标设备 1920×1080 仍需发布前实测。
下一步：执行测试、审核和验收，确认最终渲染中不再出现红框所指的卡片容器。

## AC 映射

- AC-001：selecting 使用中心放大层，保留 Canvas 到中心层的透明交接。
- AC-002：revealed 复用中心放大层，不再切换到最终卡片。
- AC-003：删除卡片样式后继续保持移动端、减弱动效和无滚动约束。
