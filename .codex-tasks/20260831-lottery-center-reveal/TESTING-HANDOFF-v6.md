任务：调整大屏活动名与奖品信息布局
输入版本：TASK-v5；开发输入：DEVELOPMENT-HANDOFF-v5
状态：completed
结论：实现通过自动化回归、类型检查、生产构建、差异校验和本地大屏尺寸/内容检查。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0，`lottery globe tests passed`。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0，Vite 生产构建完成。
- `git diff --check`：退出码 0。
- 1280×720 本地大屏检查：Header 活动名为“测试活动”，顶部奖品名为“iphone19”，奖品图 `complete=true` 且 `naturalWidth=400`；标题区 `top=81`、`bottom=188`，抽奖面板从 y=202 开始，`scrollWidth=1280`、`scrollHeight=720`。

变更文件：测试阶段未新增生产代码或测试资产；使用开发阶段已更新的布局断言。
风险或阻塞：未单独运行真实移动设备截图；移动端规则由类型/构建和静态断言覆盖，发布前仍建议在目标设备复核。
下一步：进入只读代码审核。
