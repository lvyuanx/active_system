任务：中奖结果区域展示用户头像
输入版本：TASK-v11
状态：completed
结论：正常中奖结果区已增加用户头像；当前轮次优先使用参与者真实头像，历史结果使用稳定本地头像兜底，沉浸式阶段不提前显示。
证据：

- `LotteryScreen.vue` 增加中奖头像状态、参与者匹配和稳定本地头像回退，并在恢复结果区渲染头像。
- `LotteryScreen.css` 增加头像圆形边框、光晕和入场动画；immersive 状态仍隐藏整个正常结果区。
- `test-lottery-globe.mjs` 覆盖头像 DOM、头像选择逻辑和结果区样式断言。

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
