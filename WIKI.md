# 项目知识

## 架构概览

项目采用 Monorepo，包含一个 FastAPI 模块化单体后端和三个 Vue 3 前端应用：Element Plus 管理端、ECharts 大屏端、Vant 4 用户端。

## 数据隔离

活动业务数据通过 `activity_id` 进行隔离。所有活动相关查询和写入都必须携带活动上下文。

## 管理员认证与活动生命周期

管理端使用 HS256 JWT Bearer Token，登录接口只允许 `is_superuser` 用户成功。
超级用户由环境变量初始化，密码使用 PBKDF2 哈希保存。活动状态为 `closed`、`open`、`ended`，
状态转换由后端校验：`closed <-> open` 可反复切换，非结束状态可手动转为 `ended`，结束后不可恢复。

活动用户存储在 `activity_users` 表中，以 `activity_id` 隔离；同一活动内手机号唯一。
用户 JWT 携带活动 ID，用户端按 `active_user_token:{activity_id}` 缓存 token。
管理端二维码目标地址使用 `VITE_USER_WEB_BASE_URL` 拼接 `/activity/{activity_id}`。

### 活动用户头像

`activity_users.avatar_id` 按 `(activity_id, id)` 独立保存，取值为 1–20。
新用户注册时在插入事务中使用安全随机数分配头像；旧表初始化只添加可空列，不批量填充，
并用 SQLite `BEGIN IMMEDIATE` 串行化字段迁移。登录和 `/me` 对空值用户执行带
`avatar_id IS NULL` 的条件更新，已有头像不会替换，竞争失败时读取胜者值，仍为空才返回错误。

用户端头像由 `ActivityAvatar.vue` 将 1–20 固定映射到本地卡通 SVG。活动首页和“我的”页使用用户已分配的 `avatar_id`；
聊天消息行在协议不携带发送者头像字段的前提下，当前用户使用自身 `avatar_id`，其他发送者使用稳定活动用户 ID 的本地确定性映射，
不加载外部资源、不解析路径或 HTML。

活动聊天室消息存储在 `activity_chat_messages`，通过 `activity_user_id` 关联发送者，并按 `(activity_id, message_id)`
提供游标查询。活动用户 JWT 额外携带稳定的 `activity_user_id`；缺少该 claim 的旧令牌仅在同活动用户名唯一时兼容。
用户端活动壳下包含 `/activity/{activity_id}`、`/chat`、`/me` 三个入口，WebSocket 首帧需发送 `auth`。

## 用户端移动端视觉

- 用户端活动入口采用 Vue 3 + Vant 4，认证页保留圆环 A 标识和哑金主操作；登录后壳不显示顶部 Header，
  直接展示活动状态、用户摘要和已有服务入口，并由壳层保留顶部 safe-area。
- 活动页视觉规则集中在 apps/user-web/src/views/activity/activity.css、chat.css 与 activity-auth.css，
  所有选择器使用活动页命名空间；炭黑和深灰用于层次承载，哑金用于品牌强调，
  成功和结束状态使用独立状态色。
- 登录后活动壳使用首页、聊天、“我的”三个命名嵌套路由驱动底部 Tabbar；当前项使用金色图标、
  金色加粗文字和可见包裹背景高亮，直接访问、刷新和历史导航时均以当前路由为准。
- 聊天页不再扣除顶部 Header 高度；消息区采用头像、用户名、时间和左右圆角气泡的微信式排列，
  输入框固定在 Tabbar 上方，默认一行与 44px 发送按钮等高并支持 1–3 行自适应，
  超过三行在控件内滚动；聊天 Field 不显示内部 `::after` 分隔线。
- 活动入口需要适配 320px 起的移动宽度、短屏和 safe-area inset，动态活动名称、描述和用户名必须允许换行，不得造成横向溢出。

## 本地端口

- FastAPI：8000
- 管理端：5173
- 大屏端：5174
- 用户端：5175

## 启动入口

- Windows 双击 `start.cmd`，或执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`，会分别打开后端和前端窗口。
- 执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1 -Docker` 会通过 Compose 构建并启动全部容器。

## Codex 子 Agent 配置

- 项目级线程上限配置在 `.codex/config.toml` 的 `[agents] max_threads`，当前值为 6。
- `.codex/agents/*.toml` 会被 Codex 自动发现；角色文件使用顶层 `name`、`description`、`model`、
  `model_reasoning_effort`、`sandbox_mode` 和 `developer_instructions`，不要嵌套 `[agents]` 表。
- `agents.enabled`、`agents.max_concurrent_threads_per_session` 和默认子 Agent 模型字段不是当前桌面端
  支持的项目配置键，写入后会导致任务创建时报 `expected struct AgentRoleToml`。
