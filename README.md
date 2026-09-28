# 活动系统

基于 FastAPI 和 Vue 3 的多端活动系统 Monorepo，包含：

- `apps/backend`：FastAPI 模块化单体后端。
- `apps/admin-web`：Vue 3 + Element Plus 管理端。
- `apps/screen-web`：Vue 3 + ECharts 活动大屏，以及 Electron 弹幕渲染层。
- `apps/user-web`：Vue 3 + Vant 4 用户端。
- `apps/danmaku-desktop`：Electron Windows 弹幕悬浮工具。

## Linux 服务器部署

开发机执行 `python deploy/build.py`，将打包后的整个 `deploy` 目录复制到服务器。
首次复制 `.env.example` 为 `.env` 并填写凭据，然后在该目录执行
`docker compose --env-file .env up -d --build --wait`。服务器只需 Docker Compose 和镜像/依赖下载网络。
`activate-nginx` 和 `activate-backend` 不向宿主机发布端口，统一加入 `open-getaway-network`；外部网关应转发至
`activate-nginx:8080`，由 Nginx 继续反代 `/api/` 至 `activate-backend:8000`。代码只读挂载、数据独立持久化。
更新前停服备份，保留服务器配置及运行数据；完整步骤见 [部署说明](deploy/README.md)。
生产二维码与大屏默认使用当前站点来源及对应子路径；开发仍使用 5175/5174，显式 VITE 地址优先。

## 本地开发

环境要求：Node.js 22+、pnpm 11+、Python 3.11+。

```powershell
pnpm install
python -m pip install -e ".[dev]" --directory apps/backend
uvicorn app.main:app --app-dir apps/backend --reload --port 8000
pnpm dev:admin
pnpm dev:screen
pnpm dev:user
pnpm dev:danmaku
```

本地地址：

- 管理端：http://localhost:5173
- 大屏端：http://localhost:5174
- 用户端：http://localhost:5175
- API 文档：http://localhost:8000/docs

`pnpm dev:danmaku` 需要先运行 `pnpm dev:screen`，桌面工具会加载该本地渲染服务。直接访问大屏端仍显示普通活动大屏；
Electron 仅通过 `?danmaku-overlay=1` 加载透明弹幕渲染层。

## 管理员活动管理

启动后端前复制 `.env.example` 为 `.env`，设置 `SUPERUSER_USERNAME`、`SUPERUSER_PASSWORD`、`LOTTERY_SECURITY_CODE` 和随机的 `JWT_SECRET`。
可选设置独立的 `DANMAKU_TOKEN_SECRET`；为空时弹幕 token 使用 `JWT_SECRET` 派生。后端首次启动会初始化 SQLite 数据库和超级用户；只有该超级用户可以登录管理端。
奖品图片和聊天表情包由管理员通过独立 multipart 接口上传，默认保存到 `MEDIA_ROOT=./data/media`；奖品支持 JPEG、PNG、WebP，
聊天表情额外支持 GIF，单文件上限均为 5 MiB。Docker 部署将数据库和媒体一起持久化，配置 JSON 和聊天消息不承载图片二进制。

登录后默认进入活动选择页。活动状态为“已关闭”“进行中”“已结束”：新建活动默认为已关闭，可在已关闭和进行中之间反复切换；管理员手动结束后不可再次开启或关闭。活动名称必填，描述、开始时间和结束时间可选，若同时填写时间则结束时间必须晚于开始时间。

点击活动卡片进入活动管理页；活动列表卡片底部和活动管理首页的“活动入口”面板都提供“打开抽奖大屏”按钮，会在新标签页打开该活动的实时抽奖大屏。大屏地址由管理端 `VITE_SCREEN_WEB_BASE_URL` 配置（默认 `http://localhost:5174`），并自动附加当前活动的 `activity_id`。活动管理首页会生成用户端地址和二维码。二维码地址由管理端 `VITE_USER_WEB_BASE_URL` 配置（默认 `http://localhost:5175`）。用户端按活动收集用户名和手机号，手机号在同一活动内唯一；登录 token 按活动 ID 缓存，缓存有效时扫码可直接进入活动首页。

登录活动后，用户端底部提供“首页 / 聊天 / 我的”三个入口。每个活动自动拥有聊天室：`open` 活动可发送
1–500 字符文本或点击发送活动表情，`closed` 或 `ended` 活动可查看历史但只读。表情包在管理端的活动级“聊天表情包”页面维护，
移动端只显示当前活动启用的表情；聊天消息通过 HTTP 游标接口读取，并使用首帧认证的 WebSocket 实时广播。
Nginx 已配置 WebSocket Upgrade。

活动用户注册成功时会从二十款炭黑/哑金卡通 SVG 头像中随机分配一款；头像按活动和活动用户独立保存。
历史用户在成功登录或调用 `/me` 时惰性补齐。聊天页采用微信式消息行：头像、真实用户名、时间和气泡按发送者左右对齐展示；
消息行头像使用稳定的活动用户 ID 做本地映射，不进入聊天消息或 WebSocket 协议。

## WebSocket 实时抽奖

活动管理页的“实时抽奖”入口通过管理员连接
`/api/v1/admin/activities/{activity_id}/lottery/ws` 控制开奖和重置，连接首帧发送管理员 JWT；奖项、奖品和抽奖规则通过
`GET/PUT /api/v1/admin/activities/{activity_id}/lottery` 配置；管理端“特殊配置”入口需先调用
`POST /api/v1/admin/activities/{activity_id}/lottery/security-code/verify` 校验 `LOTTERY_SECURITY_CODE`，名单通过
`GET/PUT /api/v1/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}` 按指定奖品分页搜索和单行即时保存；不同奖品分别维护黑白名单，参与者统计和规则说明仅在验证后的弹窗内展示，中奖历史通过
`GET /api/v1/admin/activities/{activity_id}/lottery/history` 查询。抽奖先发送 `lottery.draw.start` 开始球体动画，
收到 `lottery.draw.started` 后发送 `lottery.draw.stop` 才会开奖；开奖事务提交后才广播，轮次 ID保证重复停止幂等。

公开大屏连接 `/api/v1/activities/{activity_id}/lottery/ws`，不携带管理员凭证；连接成功通过 `lottery.ready` 恢复快照和进行中的轮次，
开始事件包含开始时冻结的活动用户头像与用户名，停止时先广播仅含轮次 ID 的 `lottery.draw.stopping` 让球体立即冻结并打散，
事务提交后再由 `lottery.drawn` 触发中奖者聚焦和揭晓，不返回手机号或名单标记。
大屏地址可以使用 `http://localhost:5174/?activity_id={activity_id}`，断线会指数退避重连并按 `draw_id` 去重，重置前管理端要求二次确认。

奖品可绑定图片。管理端先保存奖品配置，再通过独立图片接口上传、替换或移除；公开大屏只收到活动隔离的安全图片引用。
图片校验真实 MIME、扩展名和大小，旧资源在提交后清理，启动和配置操作会扫描孤儿文件；无图或加载失败时保留文字和库存展示。

## 弹幕桌面工具

在某个活动的管理页打开“弹幕工具”，可设置轨道数量、字体大小、不透明度、飞行时长、入场间隔、队列最大等待时间、显示区域和文字颜色。
入场间隔默认为 1 秒，可设置为 0.1–5.0 秒；上一条弹幕完整进入后经过该间隔即可尝试同轨道入场，队列最大等待时间默认为 1.5 秒。
保存后会立即推送给已运行的投屏器。页面会显示该活动的当前 token；重新生成 token 会使旧 token 和已连接的投屏器立即失效。

管理端同时提供“真实弹幕测试”开关。启动前可以配置测试人员数量（至少 1 人，不设上限）以及每条弹幕的随机延迟范围（0 至 60 秒），
开启后每个带“弹幕测试用户”标识的活动用户都会独立发送消息，通过真实聊天室写入并广播，因此聊天室和弹幕投屏器都会收到这些消息；
其中约 30% 的测试消息会在当前活动存在启用表情包时随机发送表情，表情下架或没有启用表情时自动回退为文本；关闭按钮会停止继续发送。
只有进行中的活动可以开启测试。

打开桌面工具后，粘贴 token、填写 API 地址并勾选一个或多个投屏显示器，弹幕会同步显示在所有选中的屏幕。弹幕窗口显示聊天文字和表情图片/GIF，使用透明、置顶和鼠标穿透窗口，
启动控制窗口默认尺寸为 680×720，页面默认不显示滚动条；弹幕覆盖层仍按目标显示器全屏显示。
不会接管底层应用的鼠标操作。首次启动不会回放旧聊天；断线后会按消息 ID 补齐工具运行期间漏掉的新消息。

开发时先运行 `pnpm dev:screen`，再运行 `pnpm dev:danmaku`。Windows x64 NSIS 安装包使用以下命令生成：

```powershell
pnpm dist:danmaku:win
```

输出位于 `apps/danmaku-desktop/release/`。桌面工具不把 token 写入本地存储、文件或安装包配置。

## 验证

```powershell
pnpm build
python -m pytest -q apps/backend
pnpm --filter @active/screen-web test
pnpm --filter @active/danmaku-desktop typecheck
pnpm dist:danmaku:win
```

## API 类型生成

先启动后端，再运行：

```powershell
pnpm generate:api -Target all
```

生成结果分别写入三个前端应用的 `src/api/generated/`，不使用共享 `packages/` 目录。

## Codex 任务配置

项目级子 Agent 配置位于 `.codex/config.toml` 和 `.codex/agents/`。线程上限使用
`[agents] max_threads`；角色 TOML 会自动发现，不要在配置中使用 `agents.enabled` 或在角色文件中嵌套
`[agents]` 表。
