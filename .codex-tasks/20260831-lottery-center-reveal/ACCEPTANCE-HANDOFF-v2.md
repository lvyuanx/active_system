任务：移除最终中奖卡片
输入版本：TASK-v2；审核输入：REVIEW-HANDOFF-v3
状态：completed
结论：ACCEPTED
证据：

- `pnpm --filter @active/screen-web test`、`typecheck`、`build` 和 `git diff --check` 均退出码 0。
- 源码扫描确认不存在 `data-winner-card`、`class="globe-winner"`、`.globe-winner {` 和 `globe-winner-in`；`data-winner-focus` 保留在 selecting/revealed 条件中。
- 1280×720 与 390×844 既有隔离浏览器证据确认页面无溢出、控制台无 error/warn；本次仅移除卡片容器，不改变布局尺寸。

变更文件：验收阶段未修改文件。
风险或阻塞：未重新截取 selecting/revealed 单帧；以静态阶段约束和自动化验证确认最终卡片不再渲染。真实 1920×1080 设备仍需发布前实测。
下一步：清理任务图 v2 登记的临时资源并完成最终工作树审计。

## 逐项验收

- AC-001 PASS：中奖用户放大层在 selecting 显示，红框所指的最终矩形卡片不再渲染。
- AC-002 PASS：进入 revealed 后复用同一中心头像/姓名层，源码和 CSS 中不存在 `data-winner-card` 或 `.globe-winner`。
- AC-003 PASS：减弱动效、长用户名和移动端规则保留；screen-web 构建和 390×844 无溢出证据通过。
