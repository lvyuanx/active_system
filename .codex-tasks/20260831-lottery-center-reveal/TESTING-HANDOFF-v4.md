任务：抽奖进行中标签展示奖品图片
输入版本：TASK-v3；开发输入：DEVELOPMENT-HANDOFF-v3
状态：completed
结论：实现通过自动化回归、类型检查、生产构建、差异校验和只读浏览器布局检查。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0，`lottery globe tests passed`，包含本次标签图片源码断言。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0，Vite 生产构建完成。
- `git diff --check`：退出码 0。
- 1280×720 本地大屏 DOM 检查：`scrollWidth=1280`、`scrollHeight=720`；当前奖品板 3 张图片 `complete=true` 且 `naturalWidth=400`。

变更文件：测试阶段未新增生产代码或测试资产；使用开发阶段已更新的 `test-lottery-globe.mjs`。
风险或阻塞：没有真实进行中轮次，因此未覆盖真实标签动画截图；源码与编译验证已覆盖渲染条件和图片回退路径。
下一步：进入只读代码审核。
