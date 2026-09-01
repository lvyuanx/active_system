任务：独立验证抽奖球体中心揭晓实现
输入版本：TASK-v1
状态：blocked
结论：首次测试角色仅完成 screen-web 测试，typecheck 在执行中被中断，未形成完整测试门禁结论。
证据：`pnpm --filter @active/screen-web test` 退出码 0；首次测试角色未提供 typecheck、build、浏览器和 diff 检查的可复核退出码。
变更文件：无
风险或阻塞：测试角色交接不完整，不代表代码测试失败；需要主流程补跑剩余命令。
下一步：使用同一 TASK-v1 重新执行完整前端测试和静态 AC 检查。

测试环境：Windows，Node `v22.21.1`，pnpm `11.16.0`，工作区 `D:\projects\active_system`。
用例与 AC 映射：AC-001/002/003 仅有静态证据，真实 selecting 单帧、移动端和减弱动效未完成。
回归范围：screen-web 既有消息顺序、任务调度、弹幕布局、开奖顺序、球体数学和中心层静态断言。
测试资产：无新增测试文件；后续补测沿用 `test-lottery-globe.mjs`。
覆盖缺口：首次交接时缺少 typecheck、build、diff 检查和浏览器 UI 证据。
