任务：验证管理端实时抽奖奖品行对齐修复
输入版本：TASK-v1 + DEVELOPMENT-HANDOFF-v1
状态：completed
结论：自动化检查和编译产物检查通过；样式已编译为奖品行顶部对齐，既有响应式断点和抽奖回归脚本未受影响。
证据：

- `pnpm --filter @active/admin-web typecheck`：退出码 0。
- `pnpm --filter @active/admin-web build`：退出码 0；仅报告已有依赖注释和 chunk 体积提示。
- `pnpm --filter @active/admin-web test:lottery-image-race`：退出码 0，输出 `lottery image save race guards passed`。
- 源码与 `apps/admin-web/dist/assets/index-D6Tx4o5m.css` 静态断言：奖品行 `align-items: start`、奖项头部 `align-items: center`、800px/520px 断点均通过，退出码 0。
- `apps/admin-web/src/views/lottery/lottery.css:72-106` 的实际编译结果包含 `.prize-row[data-v-d55ff658]{...align-items:start}`，未恢复旧的整行居中声明。

变更文件：

- 无；测试仅读取源码和构建产物。

风险或阻塞：本地管理端路由需要登录；浏览器视觉复核未输入凭据，且浏览器安全策略拒绝了临时 data URL 布局夹具，因此未声称完成已登录页面的真实截图验收。静态 CSS 和编译产物证据覆盖布局规则，实际登录后的浏览器截图仍是可选补充。
下一步：交由审核和验收阶段复核。
