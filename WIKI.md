# 项目知识

## 架构概览

项目采用 Monorepo，包含一个 FastAPI 模块化单体、三个 Vue 3 前端应用和一个 Electron Windows 弹幕工具：
Element Plus 管理端、ECharts 活动大屏（同时提供 Vue 弹幕渲染层）、Vant 4 用户端和 `danmaku-desktop`。

## 数据隔离

活动业务数据通过 `activity_id` 进行隔离。所有活动相关查询和写入都必须携带活动上下文。

## 管理员认证与活动生命周期

管理端使用 HS256 JWT Bearer Token，登录接口只允许 `is_superuser` 用户成功。
超级用户由环境变量初始化，密码使用 PBKDF2 哈希保存。活动状态为 `closed`、`open`、`ended`，
状态转换由后端校验：`closed <-> open` 可反复切换，非结束状态可手动转为 `ended`，结束后不可恢复。

活动用户存储在 `activity_users` 表中，以 `activity_id` 隔离；同一活动内手机号唯一。
用户 JWT 携带活动 ID，用户端按 `active_user_token:{activity_id}` 缓存 token。
管理端二维码目标地址使用 `VITE_USER_WEB_BASE_URL` 拼接 `/activity/{activity_id}`。

参与者管理由超级管理员通过 `/admin/activities/{activity_id}/participants` 访问，列表和状态操作始终带活动条件。
`activity_users.is_muted` 为持久禁言标记，禁言只禁止聊天室发言；`is_active` 为可恢复的停用标记，停用会递增
`session_version`，使已有活动用户 token 失效，恢复后必须重新登录。用户名、手机号、加入时间和两个状态字段由管理端展示。

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
聊天室每次发送都会重新检查参与用户的 active/muted 状态；禁言返回 `chat.error`/`muted`，停用后的现有连接返回未授权并关闭，
聊天历史不会因管理操作删除。用户端收到未授权聊天错误后会清除当前活动 token 并停止重连，回到活动入口。

### 聊天表情包

`activity_chat_stickers` 按活动保存表情名称、随机媒体标识、存储 key、MIME、大小、宽高和启用状态。管理员通过
`/admin/activities/{activity_id}/chat/stickers` 逐文件上传、下架和恢复，用户通过 `/activities/{activity_id}/chat/stickers`
读取当前活动启用列表。聊天消息增加 `message_type` 和 `sticker_id`，表情消息的 `body` 保留 `[表情] 名称` 兼容占位；
历史消息引用不会因下架而失效。图片使用 `/api/v1/activities/{activity_id}/chat/stickers/{sticker_id}/image?v={image_id}`
公开版本化访问，允许大屏 `<img>` 无管理员凭证加载。

## 活动弹幕

`activity_danmaku_settings` 以 `activity_id` 为主键保存轨道、字体、不透明度、飞行时长、同轨道入场间隔、碰撞避让队列最大等待时间、
显示区域、文字颜色、token 版本和更新时间。`entry_interval_seconds` 默认 1.0 秒、范围为 0.1–5.0 秒；`max_wait_seconds`
默认 1.5 秒、范围为 0.5–5.0 秒；旧数据库启动时只增量增加缺失列。
活动创建事务会初始化默认记录；旧活动仍可由服务按需补齐。当前 token 为
`dm1.{activity_id}.{token_version}.{HMAC}`，HMAC 使用 `DANMAKU_TOKEN_SECRET`，为空时使用 `JWT_SECRET`；数据库不保存明文。
播放设置和活动状态变化不会轮换 token，只有管理员手动刷新才会递增版本并断开该活动所有弹幕 WebSocket。

弹幕 HTTP/WS 只接受该只读 token，聊天发言成功后向弹幕通道发送 `message_id`、`activity_id`、`body`、`message_type`、
可选 `sticker` 和 `created_at`，不发送用户名或活动用户身份。设置保存会通过 `danmaku.settings.updated` 实时生效。
文本聊天室发送协议保持兼容，并新增独立 `sticker_id` 发送分支。

## WebSocket 实时抽奖

`lottery` 模块使用 `lottery_configs`、`lottery_awards`、`lottery_prizes`、`lottery_prize_entries` 和 `lottery_draws` 等活动隔离表。
旧的 `lottery_entries` 仅作为历史活动级名单的迁移来源，`lottery_prize_entry_migrations` 记录每个活动的一次性迁移；新参与者不预创建名单行，
缺失的奖品名单按默认可参加处理。配置 HTTP 接口是
`/admin/activities/{activity_id}/lottery`，名单分页和单行更新接口是其带 `prize_id` 查询参数的 `/entries`，历史接口是其 `/history`；管理员控制连接是
`/admin/activities/{activity_id}/lottery/ws`，公开大屏连接是 `/activities/{activity_id}/lottery/ws`。
管理端名单入口先调用 `/admin/activities/{activity_id}/lottery/security-code/verify`；该接口只接受超级用户 JWT 和请求体中的安全码，
安全码由后端 `LOTTERY_SECURITY_CODE` 配置，不返回给前端。主页面仅保留“特殊配置”入口，弹窗先选择奖品，再展示该奖品的参与者统计和规则说明；
名单状态与摘要均按 `(activity_id, prize_id, activity_user_id)` 隔离，名单更新后的摘要仍由接口响应回写。

开奖 service 在 `BEGIN IMMEDIATE` 事务内先按 `(activity_id, request_id)` 查幂等记录，再校验活动为 `open`、奖品库存、启用状态、
黑名单/白名单、活动用户 `is_active` 和跨奖品不重复规则。管理员先发送 `lottery.draw.start`，后端按活动维护单个内存轮次，
冻结开始时全部活动用户和当时的合资格用户 ID；停止时发送 `lottery.draw.stop`，只在冻结池中重新复核有效用户并写入中奖记录。
停止请求先把轮次标记为 stopping 并广播仅含轮次 ID 的 `lottery.draw.stopping`，让公开大屏冻结旋转并执行打散动画；剩余库存由奖品数量减中奖记录计数得到；事务提交后才广播管理员完整 `lottery.draw.result` 和带轮次 ID的公开脱敏
`lottery.drawn`。管理员连接首帧必须提供超级用户 JWT，带活动上下文的用户 JWT 会被拒绝；大屏不能发送控制命令。
`lottery.ready` 带有进行中的 `active_round`，公开开始事件只带活动用户 ID、用户名和头像 ID，不带手机号、名单标记、停用状态或管理员字段。

公开大屏在 `scattering` 完成且收到匹配轮次的 `lottery.drawn` 后进入 `selecting`：中奖者保留从打散位置向舞台中心移动的 Canvas 轨迹，
随后交接到中心用户层做明显的缩放揭晓；非中奖者渐隐，中心用户层持续展示到 `revealed`，不再额外切换矩形中奖卡片。中心层只渲染公开用户名和头像，不参与开奖控制。

连接管理器为单进程活动房间实现，按 `admin`/`screen` 角色广播并在断开或发送失败时清理连接；轮次状态同样只保存在当前进程，服务重启会取消未落库轮次。管理端和大屏端均使用指数退避重连；
大屏把 ready 历史作为已揭晓 `draw_id` 基线，后续事件去重后按序播放约 3 秒滚动揭晓。多副本部署仍需引入共享消息总线，不能把当前
进程内 manager 当作跨实例广播方案。

Windows 弹幕桌面工具在成功校验 token 后，通过 Electron `safeStorage` 将最近一次 token 加密保存到用户数据目录；启动页下次打开时通过受限 IPC 自动填充。
安全存储不可用时不写入明文，工具仍可手动输入 token 启动。

当活动用户较多时，球体渲染仍保留全部用户点位，但使用人数分层档位限制前景头像和姓名数量；姓名使用屏幕空间矩形避让，未进入细节预算的用户绘制为低成本光点。高密度档位每两帧绘制一次，并将设备像素比限制在 1.25 以内；头像圆形裁剪图和球体引导线使用 Canvas 缓存，停止/揭晓阶段仍强制完整绘制。

### 奖品图片媒体

`lottery_prizes` 的 `image_id`、`image_storage_key`、`image_mime` 和 `image_size` 均可为空，旧数据库启动时按列增量迁移。
媒体根目录由 `MEDIA_ROOT` 配置，奖品图片存于 `lottery-prizes/`，聊天表情存于 `chat-stickers/`，临时上传存于 `.tmp/` 对应命名空间；
服务端使用随机 key，奖品只接受真实 JPEG、PNG、WebP，聊天表情额外接受 GIF，单文件均不超过 5 MiB。

管理端图片通过独立 multipart 上传、删除和管理员读取接口处理，现有 lottery 配置 PUT 保持纯 JSON。
公开配置、快照和开奖事件只包含 `/api/v1/activities/{activity_id}/lottery/prizes/{prize_id}/image?v={image_id}` 安全引用，
公开图片路由不接受管理员凭证；旧版本引用在替换后返回 404。替换/删除提交后清理旧文件，启动和配置操作执行孤儿扫描。

大屏进行中的顶部奖品标签不依赖开始轮次载荷新增字段，而是使用当前轮次的 `award_id`、`prize_id` 从公开快照匹配奖品图片；
图片缺失或加载失败时保留奖项和奖品文字。

大屏顶部活动标题区通过内容顶部留白、标题字号/行高及主面板上方间距共同控制；桌面、移动端和短屏均采用紧凑值，
避免标题区占用过多视口而压缩抽奖球体空间。

大屏 Header 只保留品牌和连接状态，活动名称动态写入浏览器 `document.title`；顶部标题区域显示当前奖品名称和图片，当前轮次优先，其次使用最近开奖结果或下一件有库存奖品；
主抽奖面板只承载抽奖状态、球体和中奖者，避免重复显示奖品信息。
顶部当前奖品图片使用 80×80px 桌面尺寸、64×64px 移动端尺寸，图片加载失败时隐藏图片但保留名称。
普通非沉浸式页面按宽高比适配：1:1 方屏和横屏始终使用主抽奖区/奖项进度板左右并列；严格小于 1:1 的竖屏使用上下分区，奖项进度板限制高度并在自身区域滚动，避免覆盖主抽奖区或产生页面滚动。
收到开始轮次后，大屏进入沉浸式视图，仅保留铺满视口的球体；停止后的中奖者中心放大完成并短暂展示后清理 `activeRound`，恢复 Header、奖品区、奖项板和底部信息。
恢复后的中奖结果区同时显示用户头像和用户名；当前轮次使用参与者头像 ID，历史结果使用稳定本地头像兜底。
奖品板按 `prize_id` 将中奖用户名显示在对应奖品下方；无中奖记录的奖品不显示空标签。

管理端奖品编辑行的左列包含名称输入和图片操作两行，数量、启用和删除控件使用顶部对齐以匹配名称输入首行；奖项头部仍保持居中，
800px 和 520px 以下继续使用既有网格堆叠规则。

管理端弹幕页的真实测试开关由后端 `DanmakuTestManager` 驱动。任务按启动请求配置的人员数量，为活动创建或复用带
“弹幕测试用户”标识的活动用户，并为每个用户启动独立发送循环；每个循环调用聊天 service 将测试正文写入
`activity_chat_messages`，再广播标准聊天室事件和弹幕摘要。每条消息约有 30% 概率从当前活动启用表情中随机选择；没有启用表情时继续发送文本，
若表情在创建前被下架则回退文本。消息之后按配置的最小和最大延迟做均匀随机等待，因此测试消息可被聊天室、弹幕 WebSocket 和弹幕历史接口共同观察。
人员数量至少为 1 且不设应用层上限，测试用户头像编号在现有 20 个资源中循环复用；延迟限制为 0 至 60 秒且最大延迟不能小于最小延迟；
任务仅允许在 `open` 活动运行，停止测试后不再产生新消息。

管理端弹幕播放设置的文字颜色选择器关闭透明度并固定 `hex` v-model 格式；保存请求因此只提交 `#` 加六位十六进制
颜色，后端仍负责最终格式和值域校验并将成功回包规范化为大写十六进制。

管理端活动管理壳复用 `ActivitySidebar`。桌面端侧栏通过 `align-self: start`、视口高度和 `position: sticky` 与右侧内容解耦，右侧长页面不会撑高菜单；侧栏自身允许纵向滚动，移动端在 800px 断点以下恢复单列普通流和自然高度。

管理端活动列表中的每张活动卡片和单活动管理首页的“活动入口”面板都提供“打开抽奖大屏”入口，使用 `VITE_SCREEN_WEB_BASE_URL` 作为大屏基础地址，并附加完整 `activity_id` 查询参数在新标签页打开；卡片主体仍进入活动首页，底部按钮不会触发主体跳转。

Electron 主进程在内存保留 token、session 和 `displayIds`，预加载层通过受限 IPC 把它提供给 `screen-web` 渲染器；
为每个选中显示器创建透明、置顶、不可聚焦并鼠标穿透的覆盖窗口。启动控制窗口默认 680×720，页面默认隐藏滚动条。
首次连接不回放历史，重连按最后消息 ID 补齐；队列最多保留 200 条，溢出时丢弃最旧消息。
普通 `screen-web` 入口继续显示活动数据大屏，只有 `?danmaku-overlay=1` 才进入 Electron 的透明弹幕渲染层。
恢复完成后的连续 WebSocket 消息直接携带文字或表情的完整弹幕并进入渲染队列，不再为每条消息发起 HTTP 请求；ready、断线重连或
检测到 ID 缺口时，渲染器才从当前游标通过 HTTP 拉取，并把缓存的 WS 完整消息按消息 ID 合并去重，避免乱序导致遗漏。

弹幕渲染器使用 `danmaku-layout.ts` 根据 Canvas 文本宽度、视口宽度、飞行时长和 8px 间距预测运动矩形；表情展示高度默认是文字字号的 2.2 倍，
图片宽度按原始宽高比同步计算并纳入运动矩形；同轨道必须等上一条
完整进入视口后再经过 `entry_interval_seconds` 才能尝试入场，随后继续检查全轨迹碰撞；不同轨道不受该间隔限制，并从轮询游标开始选择。
所有轨道暂不可用时，消息从本地入队时间开始计时，超过 `max_wait_seconds` 后丢弃。`task-scheduler.ts` 使用单个 `requestAnimationFrame` 主循环和 `performance.now()`
派发入场刷新、节点回收、WebSocket 重连和 HTTP 重试任务；消息队列仍最多保留 200 条，弹幕横向位移由 CSS `transform`
动画完成，不通过 Vue 响应式状态逐帧重渲染。Electron 覆盖窗口关闭 `backgroundThrottling`，避免透明非聚焦窗口的动画
与调度被后台节流。

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
  超过三行在控件内滚动；聊天 Field 不显示内部 `::after` 分隔线。输入区的表情入口和发送操作使用 44px 圆形按钮承载用户提供的白色 SVG，
  分别为笑脸和纸飞机图标，笑脸主体放大显示，并提供无障碍标签；表情选择器点击输入框、输入区域外或按 `Escape` 自动隐藏。
  表情列表加载期间显示“正在加载表情”，加载完成且没有启用表情时显示“暂无表情”。
- 活动入口需要适配 320px 起的移动宽度、短屏和 safe-area inset，动态活动名称、描述和用户名必须允许换行，不得造成横向溢出。

## 本地端口

- FastAPI：8000
- 管理端：5173
- 大屏端：5174
- 用户端：5175

## 启动入口

- Windows 双击 `start.cmd`，或执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`，会分别打开后端和前端窗口。
- 执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1 -Docker` 会通过 Compose 构建并启动全部容器。
- 开发弹幕桌面工具时先运行 `pnpm dev:screen`，再运行 `pnpm dev:danmaku`；Windows x64 NSIS 安装包命令为
  `pnpm dist:danmaku:win`。

## Codex 子 Agent 配置

- 项目级线程上限配置在 `.codex/config.toml` 的 `[agents] max_threads`，当前值为 6。
- `.codex/agents/*.toml` 会被 Codex 自动发现；角色文件使用顶层 `name`、`description`、`model`、
  `model_reasoning_effort`、`sandbox_mode` 和 `developer_instructions`，不要嵌套 `[agents]` 表。
- `agents.enabled`、`agents.max_concurrent_threads_per_session` 和默认子 Agent 模型字段不是当前桌面端
  支持的项目配置键，写入后会导致任务创建时报 `expected struct AgentRoleToml`。
