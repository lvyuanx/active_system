任务：放大奖品展示图片
输入版本：TASK-v6
状态：completed
结论：顶部当前奖品图片已放大为桌面 64×64px、移动端 52×52px，并保留名称和失败回退。
证据：

- `apps/screen-web/src/components/lottery/LotteryScreenImages.css` 更新 `.title-prize__image` 默认和移动端尺寸。
- `apps/screen-web/scripts/test-lottery-globe.mjs` 增加桌面/移动端尺寸断言。
- 未修改活动 Header、奖品数据来源、开奖逻辑、球体或中奖动画。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryScreenImages.css`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/`

风险或阻塞：无；保留工作区中用户已有的其它代码和媒体变更。
下一步：进入测试、审核和场景验收。
