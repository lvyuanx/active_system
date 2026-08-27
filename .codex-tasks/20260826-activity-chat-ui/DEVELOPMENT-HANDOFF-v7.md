任务：实现“移除登录后顶部 Header、强化底部导航选中态”
输入版本：TASK-v7
状态：completed
结论：已移除登录后活动壳的全局 NavBar，并完成路由同步的底部当前项高亮、safe-area 和聊天高度调整。
证据：

- `apps/user-web/src/views/activity/index.vue:18-32` 仅渲染活动壳、嵌套路由和底部 Tabbar，
  `:model-value` 来自 `route.path` 派生值，三个入口使用命名路由目标。
- `apps/user-web/src/views/activity/index.vue:126-130` 持续从当前路径派生唯一导航索引。
- `apps/user-web/src/views/activity/activity.css:120-129` 由活动壳承接顶部 safe-area，并让首页使用新高度。
- `apps/user-web/src/views/activity/activity.css:342-371` 为当前导航设置金色、加粗文字和可见背景/边框包裹。
- `apps/user-web/src/views/activity/chat.css:1-10` 只扣除 Tabbar 和上下 safe-area，不再扣除 52px Header。
- `pnpm --filter @active/user-web typecheck` 退出码 0。
- `pnpm --filter @active/user-web build` 退出码 0，Vite 成功转换 335 个模块。
- 修改文件行数和行长扫描退出码 0；代码文件均少于 500 行，Agent 文档少于 1000 行，
  所有扫描文件均无超过 120 字符的行。
- 目标文件 `git diff --check` 退出码 0；静态扫描未发现 `VanNavBar`、`activity-nav`、
  `.van-nav-bar`、`110px` 或 `112px` 残留，路由配置无差异。
变更文件：

- `apps/user-web/src/views/activity/index.vue`
- `apps/user-web/src/views/activity/activity.css`
- `apps/user-web/src/views/activity/chat.css`
- `apps/user-web/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260826-activity-chat-ui/TASK-v7.md`
- `.codex-tasks/20260826-activity-chat-ui/DEVELOPMENT-HANDOFF-v7.md`

风险或阻塞：无开发阻塞。主工作树含前序未提交改动，本次按串行共享写入执行且未覆盖无关文件；
开发阶段按约束未启动长期服务或执行浏览器视觉验收，实际 safe-area 与交互视觉仍需 tester 独立确认。
下一步：tester 按 TASK-v7 的 AC-001 至 AC-008 执行直接访问、刷新、点击、历史导航和移动端布局回归。

## 实现摘要

- 删除登录后 `VanNavBar` 模板、组件导入和专属 CSS，认证页 `login-hero` 保留。
- 新增登录后 `activity-shell`，由其承接顶部 safe-area；首页和“我的”页移除旧 Header 高度扣减。
- 聊天壳改为只扣除 58px Tabbar 及上下 safe-area，消息区可使用移除 Header 后增加的垂直空间。
- Tabbar 当前项增加哑金图标、哑金加粗文字、半透明背景和边框包裹，未选中项保留中性弱化色。

## 技术决策

- Tabbar 使用只读 `:model-value="activeTab"`，`activeTab` 由响应式 `route.path` 计算，
  避免旧实现只在脚本初始化时赋值一次。
- 保留 Vant `route` 模式，并将 `TabbarItem :to` 改为命名路由对象。
  本地 Vant 4.10 源码表明 route 模式按 `$route.matched` 的记录路径或名称匹配，
  命名路由不会受动态参数占位符与实际路径不相等影响。
- 由 Vant Tabbar 根节点统一应用底部 safe-area，导航项不再重复添加 inset。

## AC 映射

- AC-001：`index.vue:18-33` 的登录后分支不含 Header；专属模板、导入和 CSS 已删除。
- AC-002：`index.vue:35-37` 仍保留认证分支和语义化 `login-hero`；`activity-auth.css:1-6` 保留安全区。
- AC-003：`index.vue:22-31` 使用命名路由；`index.vue:126-130` 按路径派生首页、聊天、“我的”索引。
- AC-004：点击由 Vant route 模式执行 `:to` 导航，模型值由当前路由只读派生，历史变化不会依赖点击状态。
- AC-005：`activity.css:342-371` 同时提供金色图标、金色文字、700 字重和可见背景/边框。
- AC-006：`activity.css:120-129,342-377` 分别处理顶部壳、固定 Tabbar、首页和“我的”页避让。
- AC-007：`chat.css:1-10,114-160` 使用新增高度并保留一行 44px、三行 72px 上限和内部滚动。
- AC-008：本任务未修改 API 客户端、Token、路由表、`chat.vue`、头像组件或消息协议；
  `chat.vue:74-184` 的头像、历史锚点、条件滚动、重连和发送逻辑保持原状。

## 验证结果

- 类型检查：PASS，`pnpm --filter @active/user-web typecheck`，退出码 0。
- 生产构建：PASS，`pnpm --filter @active/user-web build`，退出码 0，335 个模块完成转换。
- 静态残留检查：PASS，登录后 NavBar 标识与旧 110/112px 高度扣减均无匹配。
- 路由范围检查：PASS，`apps/user-web/src/router/index.ts` 无工作树差异。
- 格式检查：PASS，`git diff --check` 退出码 0；行数与 120 字符约束通过。

## 方案偏差

无。未修改 `router/index.ts`，未引入依赖，未改变入口名称、顺序和目标。

## 残余风险

- 开发阶段没有实际浏览器和设备 safe-area 视觉证据，需由 tester 在目标视口确认无重叠和高亮辨识度。
- 工作树已有前序聊天、头像和文档改动；本次只对冻结范围应用增量补丁，没有清理或提交这些改动。
