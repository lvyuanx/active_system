任务：抽奖球体停止后的中心放大揭晓
输入版本：TASK-v1；审核输入：REVIEW-HANDOFF-v2
状态：completed
结论：ACCEPTED
证据：

- screen-web 测试、类型检查、生产构建和 `git diff --check` 均退出码 0。
- 1280×720 隔离大屏流程收到 started/stopping/result 后进入 revealed；最终存在 1 个 `data-winner-card`、不存在残留 `data-winner-focus`，滚动尺寸为 1280×720，控制台 error/warn 为空。
- 390×844 响应式检查滚动尺寸等于 390×844，揭晓布局无横向溢出，控制台 error/warn 为空；临时视口已恢复默认。
- `test-lottery-globe.mjs` 覆盖 `winnerFocusHandoff` 0.2/0.6 边界、中心层挂载条件、revealed 卡片条件、中心放大 keyframes 和减弱动效规则。

变更文件：验收角色未修改文件。
风险或阻塞：真实 selecting 单帧没有单独截图，AC-002 的中心层时序由源码条件、Canvas 插值、handoff 数学边界、CSS 构建和完整 revealed 流程共同证明；真实 1920×1080 设备仍需发布前专项实测。
下一步：停止临时后端/Vite 测试服务、关闭临时浏览器标签，完成任务图清理节点和最终工作树审计。

## 逐项验收

- AC-001 PASS：`LotteryScreen.vue:337-345` 将匹配轮次停止事件切到 scattering；`LotteryWinnerReveal.vue:3-14` 只在 selecting/revealed 渲染中奖层，散开阶段不会提前显示中奖用户或卡片。
- AC-002 PASS：`LotteryGlobe.vue:267-293` 保留中奖者从打散坐标到中心的插值并弱化其他参与者；`LotteryGlobe.vue:300-305` 通过 `winnerFocusHandoff` 渐隐 Canvas 中奖者，`LotteryWinnerReveal.css:1-102` 让中心头像和姓名从中心缩放出现，避免双重中心绘制。
- AC-003 PASS：`LotteryWinnerReveal.vue:14` 仅在 revealed 渲染中心卡片，`LotteryWinnerReveal.css:113-147` 提供从 0.42 到 1.06 的中心回弹；1280×720 流程确认卡片存在且布局不溢出。
