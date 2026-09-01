任务：移除最终中奖卡片
输入版本：TASK-v2；测试输入：TESTING-HANDOFF-v3
状态：completed
结论：APPROVED
证据：

- `LotteryWinnerReveal.vue:2-14` 让同一个中心放大层覆盖 selecting/revealed，已不存在最终卡片 DOM、`data-winner-card` 或 `.globe-winner`。
- `LotteryWinnerReveal.css` 仅保留头像、姓名、聚光环和中心放大动画；已删除卡片背景、边框、阴影和卡片专用 keyframes。
- `LotteryGlobe.vue` 的 Canvas 交接和停止阶段未改变；`LotteryScreen.vue` 的开奖协议处理未改变。
- screen-web test/typecheck/build 与 `git diff --check` 均退出码 0；代码文件均不超过 500 行且无超过 120 字符行。
- TASKGRAPH-v1 已标记 `INVALIDATED` 并注明由 TASK-v2 取代；TASKGRAPH-v2、输入/输出清单和 SHA-256 证据已建立。

变更文件：审核阶段未修改文件。
风险或阻塞：真实 selecting/revealed 动画单帧仍未单独截取，但卡片移除由源码、静态断言、构建和既有浏览器布局证据覆盖；1920×1080 目标设备仍需发布前实测。
下一步：交由验收按 AC-001 至 AC-003 确认红框元素已移除且中心用户保持可见。

## 评审结论

- 范围符合 TASK-v2：只改中奖展示层和关联测试/文档，不改后端、WebSocket、开奖数据或管理端控制。
- 无障碍：中心层使用 `role="status"` 与 `aria-live="polite"`，最终阶段仍可播报中奖用户名。
- 响应式：中心姓名保留最大宽度和省略号，移动端维持既有视口无滚动约束。
