任务：抽奖时沉浸式球体与揭晓后恢复
输入版本：TASK-v10
状态：completed
结论：开始轮次时已隐藏外围页面并将球体铺满视口；中奖者揭晓后短暂保留中心放大层，随后清理轮次恢复正常页面。
证据：

- `LotteryScreen.vue` 新增 `lottery-screen--immersive` 状态类和 `restoreTimer`，轮次揭晓后无排队轮次时自动清理 `activeRound`。
- `LotteryScreen.css` 在沉浸式状态隐藏 Header、顶部奖品区、奖项板、底部信息、辅助文案和轮次标签，并让球体容器铺满视口。
- `LotteryGlobe.css` 在进行中和揭晓阶段隐藏球体辅助 caption，只保留球体及中奖者中心放大层。
- 重置、重连、错误和新轮次到达时会取消待恢复计时，避免旧轮次计时影响新轮次。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryScreen.vue`
- `apps/screen-web/src/components/lottery/LotteryScreen.css`
- `apps/screen-web/src/components/lottery/LotteryGlobe.css`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/`

风险或阻塞：无；保留工作区中用户已有的其它代码和媒体变更。
下一步：进入测试、审核和场景验收。
