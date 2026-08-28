任务：依据 TASK-v1 对 B站式弹幕碰撞避让改造执行回归测试。
输入版本：TASK-v1；开发交接为 DEVELOPMENT-HANDOFF-v1；输入快照为 HEAD-9ec1caa4-dirty-20260828。
状态：completed
结论：必需验收标准均有测试或静态证据覆盖，阻断测试通过；未发现需要回退开发阶段的失败。
证据：
- `python -m pytest -q`（工作目录 `apps/backend`）：31 passed；仅有既有 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用警告。
- `python -m pytest tests/test_danmaku.py -q`：弹幕定向用例通过，覆盖默认值、范围、旧 SQLite 迁移、旧请求体和 WebSocket 新字段。
- `pnpm --filter @active/screen-web test`：消息顺序、任务调度、碰撞几何三组脚本全部通过；静态断言同时确认 CSS 终点为 `translate3d(-100%, 0, 0)`，与几何终点 `left = -textWidth` 一致。
- `node apps/admin-web/scripts/test-danmaku-settings.mjs`：管理端控件范围、步长和绑定静态回归通过。
- `pnpm -r typecheck`：admin-web、screen-web、user-web 和 danmaku-desktop 四个工作区项目均通过。
- `pnpm -r build`：三个前端和 Electron 构建均通过；仅有既有 Element Plus 注释、chunk 体积提示。
- `git diff --check` 退出码为 0；碰撞函数随机采样回归 10,000 次未产生漏报碰撞（false negative 为 0）。
- AC 映射：AC-001/002 由后端定向用例覆盖；AC-003 由 HTTP 与 WebSocket 断言覆盖；AC-004/005/006/007 由 `test-danmaku-layout.mjs`、任务调度和静态断言覆盖；AC-008 由类型、构建、既有链路回归与渲染器源码检查覆盖；AC-009 由文档和全量验证覆盖。
变更文件：仅新增/调整测试脚本、测试断言和测试专用证据文档；未修改生产代码以绕过测试。
风险或阻塞：浏览器入口已验证普通大屏与 `?danmaku-overlay=1` 路由可加载；受限于浏览器无法注入 Electron 活动会话，未在浏览器中伪造 WebSocket 活动弹幕，已明确由纯几何测试、静态检查、类型检查和生产构建补足证据。
下一步：交由审核阶段检查实现范围、代码质量、文档同步和证据一致性。
