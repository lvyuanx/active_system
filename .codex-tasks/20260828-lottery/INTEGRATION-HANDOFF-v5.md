任务：将 TASK-v5 开发结果集成到主工作树并完成集成门禁
输入版本：TASK-v5 + ARCHITECTURE-v5 + DEVELOPMENT-HANDOFF-v5
状态：completed
结论：开发结果（含管理端图片保存竞态修复）已在主工作树完成重新集成，生产代码、测试和部署配置均处于可供测试角色复核的状态；未覆盖既有用户未提交改动。
证据：

- `DEVELOPMENT-HANDOFF-v5.md` 已声明实现完成，包含媒体广播、级联清理、公开版本参数和失败恢复修复。
- `python -m pytest -q apps/backend/tests`：退出码 0，55 passed，7 warnings。
- `pnpm --filter @active/admin-web test:lottery-image-race`：退出码 0，保存期间配置刷新竞态断言通过。
- `pnpm --filter @active/admin-web typecheck` 与 `build`：退出码 0。
- `pnpm --filter @active/screen-web typecheck`、`build`、`test`：退出码 0。
- `python -m compileall -q apps/backend/app apps/backend/tests`：退出码 0。
- `git diff --check`：退出码 0。
- `deploy/compose/docker-compose.yml` 已通过 PyYAML 解析，包含 backend、admin-web、screen-web、user-web 服务及 `active-media` 卷；Nginx API location 已设置 6 MiB body limit。
- 浏览器临时活动实测选择 PNG、保存、替换和移除后页面状态正确；大屏带图加载成功，删除文件后收到配置更新可回退为无图文字。
- 图片 POST/DELETE 后公开 WebSocket 实时配置广播、配置删除奖品/奖项后的媒体回收、已有中奖记录阻止删除、公开图片无 `v` 拒绝均有自动化回归。
- 目标代码文件行长检查通过（不超过 120 字符），未发现超出本任务写入范围的生产路径。

变更文件：`apps/backend/app/core`、`apps/backend/app/modules/files`、`apps/backend/app/modules/lottery`、`apps/backend/tests/test_lottery_images.py`、`apps/admin-web/src/api/client.ts`、`apps/admin-web/src/views/lottery`、`apps/screen-web/src/api/client.ts`、`apps/screen-web/src/components/lottery`、`.env.example`、部署配置、模块 AGENTS、项目知识文件和 `.codex-tasks/20260828-lottery`。
风险或阻塞：无集成阻塞；当前工作树原有 TASK-v1~v4 及其它未提交改动保留不动。单进程操作锁和 WebSocket manager 的多副本限制已在模块文档记录。
下一步：进入审核与验收阶段，复核最新 55 项测试、文件清单和主集成浏览器证据。
