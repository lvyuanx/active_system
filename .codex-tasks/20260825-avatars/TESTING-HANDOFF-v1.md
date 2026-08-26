任务：
T3｜活动用户 SVG 头像与首次登录随机分配

输入版本：
TASK-v2；架构 ARCHITECTURE-v1；开发交接 DEVELOPMENT-HANDOFF-v1；测试工作包 `wp-avatar-testing`。

状态：completed

结论：
主线程串行测试门禁通过。后端头像专项与既有聊天回归、三端 TypeScript 类型检查、三端生产构建、十款 SVG 静态扫描及浏览器移动端布局均有证据；没有发现阻断失败。

证据：

- `python -m pytest -q apps/backend`：22 passed，退出码 0；仅 `apps/backend/app/modules/chat/router.py` 的既有 FastAPI 弃用警告。
- `pnpm typecheck`：admin-web、screen-web、user-web 均通过，退出码 0。
- `pnpm build`：三个前端均构建成功，退出码 0；admin-web 保留既有 Rollup 注释/chunk 警告。
- SVG 扫描：`COUNT=10`、`DUPLICATE_HASH_GROUPS=0`、`INVALID_STATIC_ASSETS=0`。
- `git diff --check`：退出码 0；仅显示 Git 对既有工作树文件的换行转换提示。
- 浏览器检查：在 localhost 活动页以 390×844 和 320×720 视口验证首页、“我的”页头像；320px 检查结果 `viewportWidth=320`、`scrollWidth=320`、`avatarCount=1`，没有横向溢出。
- 浏览器证据已冻结在 `BROWSER-EVIDENCE-v1.md`，补充了 600px 断点和组件尺寸静态核对。
- 后端专项用例覆盖注册事务分配、登录和 `/me` 稳定返回、活动隔离、错误登录不补齐、旧 SQLite 表迁移及历史用户惰性补齐。

变更文件：

无。测试阶段未修改测试资产或生产文件。

风险或阻塞：

- 浏览器视觉检查覆盖了首页和“我的”中的当前分配头像，未逐一在真实页面切换十个 ID；十个 SVG 已通过数量、唯一哈希和静态安全扫描，资源映射由构建和类型检查覆盖。
- 未做高并发端到端压力测试；惰性补齐代码已有条件更新后读取已落库值的竞态保护。
- 全量构建的既有 Rollup 警告未处理，不影响退出码。

下一步：

交给审核角色执行只读代码、路径范围、数据兼容、安全和测试覆盖审核；随后由验收角色按 AC-001 至 AC-010 作最终结论。

测试环境：

Windows 本地工作树 `D:\projects\active_system`；Python pytest；pnpm workspace；本地 FastAPI/用户端服务已运行；浏览器使用 390×844 与 320×720 临时视口，测试后已恢复默认并清理临时标签。

AC 结果：

- AC-001 PASS：十个 SVG、唯一哈希、无脚本/外链扫描通过。
- AC-002 PASS：首页/我的展示，320px/390px 无横向溢出。
- AC-003 PASS：注册返回 1–10 头像且和数据库一致；头像分配异常时注册事务回滚。
- AC-004 PASS：重复登录和 `/me` 头像稳定。
- AC-005 PASS：返回值限制在十款集合；确定性测试验证同一活动内重复头像允许且重登不替换。
- AC-006 PASS：两个活动独立保存和读取头像。
- AC-007 PASS：旧表迁移保留 NULL，成功 `/me` 后惰性补齐并稳定。
- AC-008 PASS：错误凭证、跨活动令牌未补齐头像并保持现有状态码。
- AC-009 PASS：22 项后端回归和三端构建通过，聊天行为未回归失败。
- AC-010 PASS：跨活动重登后头像保持独立，并可继续访问聊天历史；活动 token 与稳定活动用户 ID 行为保持。

覆盖缺口：

未执行多进程 SQLite 压力测试，也未在页面中手动逐个展示十个 ID；这两项不阻断本版，因为条件更新竞态保护、静态资源扫描、固定映射和生产构建均已验证。
