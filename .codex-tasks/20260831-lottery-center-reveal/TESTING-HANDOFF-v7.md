任务：放大奖品展示图片
输入版本：TASK-v6；开发输入：DEVELOPMENT-HANDOFF-v6
状态：completed
结论：实现通过自动化回归、类型检查、生产构建、差异校验和本地大屏尺寸检查。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0。
- `git diff --check`：退出码 0。
- 1280×720 本地大屏检查：奖品图 `64×64`、`complete=true`、`naturalWidth=400`；标题区仍在视口内，`scrollWidth=1280`、`scrollHeight=720`。

变更文件：测试阶段未新增生产代码或测试资产；使用开发阶段已更新的尺寸断言。
风险或阻塞：未单独运行真实移动设备截图；移动端尺寸由静态断言覆盖，发布前仍建议在目标设备复核。
下一步：进入只读代码审核。
