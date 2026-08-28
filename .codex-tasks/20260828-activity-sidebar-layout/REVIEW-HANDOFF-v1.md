任务：TASK-v1 修复活动管理侧栏被内容撑高（审核阶段）
输入版本：TASK-v1；DEVELOPMENT-HANDOFF-v1；TESTING-HANDOFF-v1
状态：completed
结论：APPROVED。改动范围集中在管理端活动壳样式和项目知识文档，未发现会改变导航、接口或业务行为的无关修改；桌面与移动断点规则互相覆盖完整。
证据：
- `git diff -- apps/admin-web/src/styles/index.css` 仅包含侧栏独立高度、粘性定位、自身滚动和移动端回退规则。
- `apps/admin-web/AGENTS.md:26`、`MEMORY.md:35`、`LEARNING.md:42-44`、`WIKI.md:65` 已同步该布局约束和验证结论。
- 管理端 `typecheck`、`build` 和 `git diff --check` 均通过；构建仅报告既有依赖注释和 chunk 大小提示，不影响退出码。
变更文件：无审核阶段写入。
风险或阻塞：真实登录后活动页的截图未覆盖，但不构成代码审核阻断；已有测试交接明确该证据缺口。
下一步：交验收阶段逐条确认 AC。

