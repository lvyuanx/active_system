任务：抽奖球体停止后的中心放大揭晓
输入版本：TASK-v1
状态：completed
结论：保留 Canvas 中奖者从打散位置向中心移动的轨迹，新增 selecting 阶段中心用户放大层，并按 handoff 曲线让 Canvas 中奖者渐隐；revealed 阶段继续显示中心中奖卡片，未修改开奖协议和后端逻辑。
证据：

- `LotteryGlobe.vue` 委托 `LotteryWinnerReveal.vue`，后者仅在 `phase === 'selecting' && winnerName` 时渲染 `data-winner-focus`，`revealed` 才渲染 `data-winner-card`。
- Canvas 中奖者继续使用 `visualEntry` 的中心插值；`winnerFocusHandoff(selectionProgress)` 在 0.2 进度前保持原轨迹，在 0.6 进度完成透明交接。
- `LotteryWinnerReveal.css` 增加中心定位、头像/姓名缩放、光环、长用户名截断、移动端尺寸和 `prefers-reduced-motion` 回退。
- `LotteryGlobe.vue` 与 `LotteryScreen.vue` 将 selecting 阶段文案明确为“中奖者正在中心放大”。
- `pnpm --filter @active/screen-web test`、`typecheck`、`build` 均退出码 0；`git diff --check` 通过。
- 隔离 1280×720 大屏已观察到 rolling 与 revealed 阶段，布局滚动尺寸等于视口尺寸，控制台 error/warn 为空。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryGlobe.vue`
- `apps/screen-web/src/components/lottery/LotteryGlobe.css`
- `apps/screen-web/src/components/lottery/LotteryWinnerReveal.vue`
- `apps/screen-web/src/components/lottery/LotteryWinnerReveal.css`
- `apps/screen-web/src/components/lottery/LotteryScreen.vue`
- `apps/screen-web/src/components/lottery/lottery-globe-math.ts`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`、`LEARNING.md`、`WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/TASK-v1.md`

风险或阻塞：中心 selecting 帧未在浏览器中单帧截图留证，但组件挂载条件、Canvas 交接数学边界和样式静态断言已覆盖；未引入新的协议或数据风险。
下一步：交由测试角色复跑自动化验证并按 AC 检查，再进行审核和验收。

## 实现摘要

- 技术决策：中心用户层使用现有安全头像源和公开用户名，仅作为 selecting 阶段的视觉层；不使用管理员凭证、不新增依赖。
- AC-001：中心层以 selecting 条件挂载，scattering/scattered 不会提前显示中奖用户。
- AC-002：Canvas 仍负责从打散坐标到中心的运动；handoff 完成后中心层负责清晰放大和聚光，非中奖参与者沿现有 selecting 衰减。
- AC-003：revealed 阶段的中心卡片保留并增强小比例进入与轻微回弹。
- 方案偏差：开发角色未能在限定等待窗口内回传，因此由主线程按同一 TASK-v1 串行完成实现；范围、输入版本和写入范围未改变。
- 残余风险：真实 1920×1080 目标设备和极长用户名的字体差异仍需发布前专项实测。
