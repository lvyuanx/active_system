任务：按用户场景验收管理端实时抽奖奖品行对齐修复
输入版本：TASK-v1 + DEVELOPMENT-HANDOFF-v1 + TESTING-HANDOFF-v1 + REVIEW-HANDOFF-v1
状态：completed
结论：ACCEPTED
证据：

- AC-001：PASS。截图所示错位由 `.prize-row` 的整行居中声明造成；修复后源码和编译 CSS 均明确设置 `align-items: start`，数量、启用和删除控件会与名称首行顶部对齐。已登录页面截图未执行，原因已在测试交接中说明。
- AC-002：PASS。多奖品共用同一 `.prize-row` 规则，800px 和 520px 的既有网格堆叠规则未修改；断点静态断言通过。
- AC-003：PASS。管理端 typecheck、生产 build 和现有 `test:lottery-image-race` 均退出码 0；业务模板和 API 文件未改动。

变更文件：

- `apps/admin-web/src/views/lottery/lottery.css`
- `apps/admin-web/src/views/lottery/AGENTS.md`

风险或阻塞：无必需验收阻断。仅保留“未在已登录浏览器中截图”的证据限制，不影响本次最小 CSS 修复交付。
下一步：完成任务证据归档并向用户交付。
