任务：中奖用户名按奖品归属显示
输入版本：TASK-v12；开发输入：DEVELOPMENT-HANDOFF-v12
状态：completed
结论：实现通过自动化回归、类型检查、生产构建、差异校验和本地奖品板内容检查。
证据：

- `pnpm --filter @active/screen-web test`：退出码 0。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0。
- `git diff --check`：退出码 0。
- 浏览器奖品板检查：`iphone19 -> 弹幕测试用户91`、`平板电脑 -> 弹幕测试用户166`、`手机 -> 弹幕测试用户258`，每个用户名均位于对应 `.prize-item` 下。

变更文件：测试阶段未新增生产代码或测试资产；使用开发阶段已更新的静态断言。
风险或阻塞：未单独运行真实开奖；当前活动 ready 数据已足够验证多奖品归属渲染。
下一步：进入只读代码审核。
