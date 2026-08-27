任务：T3 架构门禁：活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：采用独立 `danmaku` 后端模块、活动级 SQLite 设置记录、版本化 HMAC token、独立只读弹幕 WebSocket，
以及由 `screen-web` 渲染、`danmaku-desktop` 管理窗口的 Electron 架构。方案满足 TASK-v1 的范围和
AC-001 至 AC-010。
证据：现有活动、聊天室和 SQLite 数据层均以 `activity_id` 隔离；聊天室已在持久化后通过进程内 manager
广播，适合增加独立监听者而不改变现有协议。Electron 官方 API 支持透明无框窗口、`setIgnoreMouseEvents`、
显示器枚举和无焦点全局快捷键。
变更文件：无
风险或阻塞：子 Agent 架构交接在两次受限等待内未返回，主线程根据冻结任务、源码和官方 API 记录本方案。
风险为单进程广播不能跨副本、HTTP 配置的 token 可被网络窃听、不同 Windows 窗口管理器的置顶体验；v1
仅保证本地开发 HTTP 和 Windows 优先的行为。
下一步：按本方案作为开发输入，实现后端、管理端、渲染层和桌面壳，并在集成后进行测试、审核和验收。

## 模块边界

- `app/modules/danmaku/` 管理设置、token 认证、弹幕消息分页和独立 WebSocket；只读取 `activities` 和
  `activity_chat_messages`，不具备聊天室写入能力。
- `chat/router.py` 保持既有 HTTP 和 WebSocket 协议，仅在消息已落库后额外调用 `danmaku_manager` 广播摘要。
- `admin-web` 仅调用管理员接口；`screen-web` 是无特权渲染器；`danmaku-desktop` 仅为 Windows 窗口、托盘、
  显示器选择和受限 IPC 提供宿主能力。

## 数据与 token

- 添加 `activity_danmaku_settings`，主键为 `activity_id`，保存 7 个配置字段、`token_version`、
  `token_created_at` 和 `updated_at`。首次管理员读取或写入时在事务中懒创建默认记录。
- token 格式为 `dm1.{activity_id}.{token_version}.{mac}`；`mac` 是对固定域分隔消息
  `danmaku:{activity_id}:{token_version}` 的 SHA-256 HMAC。密钥使用 `DANMAKU_TOKEN_SECRET`，为空时回退
  `JWT_SECRET`。验证时使用 `hmac.compare_digest`，并以当前数据库版本为唯一有效版本。
- 重新生成 token 只递增版本并更新时间，然后关闭该活动全部弹幕 WebSocket；不保存明文 token。

## HTTP 与 WebSocket 契约

- `GET /admin/activities/{activity_id}/danmaku`：管理员读取配置、当前 token 与 token 创建时间；懒创建设置。
- `PUT /admin/activities/{activity_id}/danmaku`：管理员完整替换配置；Pydantic 强制范围、颜色格式和显示区域关系，
  成功后向连接者发 `danmaku.settings.updated`。
- `POST /admin/activities/{activity_id}/danmaku/token`：管理员递增版本，返回新 token 与当前配置。
- `GET /danmaku/session`：`Authorization: Bearer <danmaku token>`，返回活动标识、名称、状态、配置和当前最大消息 ID。
- `GET /danmaku/messages?after_id=&limit=`：同一 token 只读取所属活动的消息摘要，按 ID 升序并带 `has_more`。
- `WS /danmaku/ws`：首帧 `{ type: "auth", token }`；成功后发送 `danmaku.ready`，之后仅接收
  `danmaku.message.created` 与 `danmaku.settings.updated`。错误格式为
  `{ type: "danmaku.error", code, detail }` 后关闭。

## 运行时与安全

- 弹幕消息摘要仅含 `message_id`、`activity_id`、`body`、`created_at`；活动状态仍由聊天写入服务控制，关闭或
  结束活动不会产生新的消息或弹幕。
- Electron launcher 通过受限 preload IPC 获取显示器、启动和停止弹幕；主进程校验 URL、token 和 display ID，
  只将运行时 token 保存在内存。渲染器关闭 Node 集成、启用上下文隔离与 sandbox，不暴露通用 IPC。
- 主进程验证 session 后创建覆盖选中显示器边界的透明、无边框、置顶、不可聚焦、跳过任务栏窗口，并调用
  `setIgnoreMouseEvents(true, { forward: true })`。显示器移除时销毁覆盖层并显示 launcher；托盘和
  `Ctrl+Shift+D` 复用停止/恢复逻辑。
- `screen-web` 连接独立 WS；第一次 `ready` 将其最大 ID 设为基线，不读取旧消息；重连时用最后已处理 ID 请求
  `/danmaku/messages` 补齐，再继续接收实时事件。轨道状态和队列留在渲染器内，设置硬上限并在溢出时 `shift()`。

## 测试重点与回滚

- 后端覆盖配置范围、活动隔离、稳定/轮换 token、HTTP/WS 认证、消息摘要、配置推送、闭合活动不产生新事件和
  游标补齐。
- 前端检查管理端类型与生产构建、渲染队列/轨道单元逻辑以及 Electron 主进程 TypeScript 编译。
- Windows 通过构建 NSIS x64 安装包、实际启动、选择显示器、鼠标穿透、托盘、快捷键和显示器移除进行手工验收。
- 回滚可删除 `danmaku` 路由与前端/桌面入口；SQLite 新表独立且不改变聊天表，不需要回滚现有数据。
