任务：抽奖球体停止后的中心放大揭晓交付审核
输入版本：TASK-v1；测试输入：TESTING-HANDOFF-v2；证据修复：INPUT-MANIFEST-v1、OUTPUT-MANIFEST-v1
状态：completed
结论：APPROVED
证据：

- `LotteryGlobe.vue:14-19` 只委托中奖展示组件；`LotteryWinnerReveal.vue:3-14` 将中心层限制在 selecting、最终卡片限制在 revealed，scattering/scattered 不会提前挂载中奖展示。
- `LotteryGlobe.vue:267-293` 保留中奖者从打散位置向舞台中心的插值；`LotteryGlobe.vue:300-305` 使用 `winnerFocusHandoff` 做 Canvas 到中心层的透明交接，避免重复绘制。
- `LotteryWinnerReveal.css:1-208` 提供中心定位、缩放、光环、回弹卡片、移动端尺寸、长用户名省略和减弱动效回退。
- `pnpm --filter @active/screen-web test`、`typecheck`、`build` 和 `git diff --check` 均退出码 0；代码文件均不超过 500 行，生产代码无超过 120 字符行。
- 任务图已同步 development/testing 成功状态、TESTING-HANDOFF-v2 引用、WorkPackage、输入/输出 SHA-256 和主树串行集成摘要；任务外奖品图片删除已在输入/输出清单中明确排除。

变更文件：审核角色未修改文件。
风险或阻塞：真实 selecting 单帧尚未单独截屏，交接时序由源码条件、数学边界、静态断言和最终浏览器流程共同覆盖；真实 1920×1080 目标设备仍需发布前实测。
下一步：交由验收角色按 AC-001 至 AC-003 做用户场景验收。

## 审核检查

- 范围：仅大屏展示组件、数学辅助、测试和对应文档；未修改后端协议、开奖数据或管理员控制。
- 兼容性：winner 不在本地 participants 时仍使用事件用户名和默认头像；`prefers-reduced-motion` 保留阶段语义并缩短动画。
- 文档：大屏模块 AGENTS、抽奖组件 AGENTS、MEMORY、LEARNING、WIKI 与任务交接已同步。
