任务：中奖用户名按奖品归属显示
输入版本：TASK-v12
状态：completed
结论：奖品板已按 `prize_id` 分组渲染中奖用户名，每个用户名显示在对应奖品下方，保留无中奖记录时的空白处理。
证据：

- `LotteryScreen.vue` 新增 `prizeDraws` 过滤函数，并将奖品行与对应 `winner-list` 放入独立 `prize-item`。
- `LotteryScreen.css` 为每个奖品块增加间距，并将中奖标签缩进到奖品内容下方。
- `test-lottery-globe.mjs` 覆盖奖品块、`prize_id` 过滤和归属渲染断言。

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
