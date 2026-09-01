任务：收紧大屏顶部标题区
输入版本：TASK-v4
状态：completed
结论：已收紧大屏内容顶部留白、活动标题字号/行高和标题到抽奖面板的间距，并同步移动端与短屏覆盖值。
证据：

- `LotteryScreen.css` 默认内容顶部 padding 从 `clamp(24px, 5vh, 62px)` 调整为 `clamp(16px, 3vh, 38px)`。
- 活动标题最大字号从 64px 调整为 52px，增加紧凑行高；主面板上方间距从 `clamp(18px, 3vh, 42px)` 调整为 `clamp(14px, 2vh, 28px)`。
- 移动端和短屏分别下调标题字号、内容顶部 padding 与面板间距；抽奖球体、奖品标签和中奖放大层未改动。
- 静态回归断言已锁定紧凑布局的关键 CSS 值。

变更文件：

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
