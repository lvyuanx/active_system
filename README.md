# 活动系统

基于 FastAPI 和 Vue 3 的多端活动系统 Monorepo，包含：

- `apps/backend`：FastAPI 模块化单体后端。
- `apps/admin-web`：Vue 3 + Element Plus 管理端。
- `apps/screen-web`：Vue 3 + ECharts 活动大屏，以及 Electron 弹幕渲染层。
- `apps/user-web`：Vue 3 + Vant 4 用户端。
- `apps/danmaku-desktop`：Electron Windows 弹幕悬浮工具。

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

启动后端前复制 `.env.example` 为 `.env`，设置 `SUPERUSER_USERNAME`、`SUPERUSER_PASSWORD` 和随机的 `JWT_SECRET`。
可选设置独立的 `DANMAKU_TOKEN_SECRET`；为空时弹幕 token 使用 `JWT_SECRET` 派生。后端首次启动会初始化 SQLite 数据库和超级用户；只有该超级用户可以登录管理端。

登录后默认进入活动选择页。活动状态为“已关闭”“进行中”“已结束”：新建活动默认为已关闭，可在已关闭和进行中之间反复切换；管理员手动结束后不可再次开启或关闭。活动名称必填，描述、开始时间和结束时间可选，若同时填写时间则结束时间必须晚于开始时间。

点击活动卡片进入活动管理页，首页会生成用户端地址和二维码。二维码地址由管理端 `VITE_USER_WEB_BASE_URL` 配置（默认 `http://localhost:5175`）。用户端按活动收集用户名和手机号，手机号在同一活动内唯一；登录 token 按活动 ID 缓存，缓存有效时扫码可直接进入活动首页。

登录活动后，用户端底部提供“首页 / 聊天 / 我的”三个入口。每个活动自动拥有聊天室：`open` 活动可发送
1–500 字符纯文本，`closed` 或 `ended` 活动可查看历史但只读。聊天消息通过 HTTP 游标接口读取，并使用
首帧认证的 WebSocket 实时广播；Nginx 已配置 WebSocket Upgrade。

活动用户注册成功时会从二十款炭黑/哑金卡通 SVG 头像中随机分配一款；头像按活动和活动用户独立保存。
历史用户在成功登录或调用 `/me` 时惰性补齐。聊天页采用微信式消息行：头像、真实用户名、时间和气泡按发送者左右对齐展示；
消息行头像使用稳定的活动用户 ID 做本地映射，不进入聊天消息或 WebSocket 协议。

## 弹幕桌面工具

在某个活动的管理页打开“弹幕工具”，可设置轨道数量、字体大小、不透明度、飞行时长、入场间隔、队列最大等待时间、显示区域和文字颜色。
入场间隔默认为 1 秒，可设置为 0.1–5.0 秒；上一条弹幕完整进入后经过该间隔即可尝试同轨道入场，队列最大等待时间默认为 1.5 秒。
保存后会立即推送给已运行的投屏器。页面会显示该活动的当前 token；重新生成 token 会使旧 token 和已连接的投屏器立即失效。

管理端同时提供“真实弹幕测试”开关。启动前可以配置测试人员数量（至少 1 人，不设上限）以及每条弹幕的随机延迟范围（0 至 60 秒），
开启后每个带“弹幕测试用户”标识的活动用户都会独立发送消息，通过真实聊天室写入并广播，因此聊天室和弹幕投屏器都会收到这些消息；
关闭按钮会停止继续发送。只有进行中的活动可以开启测试。

打开桌面工具后，粘贴 token、填写 API 地址并勾选一个或多个投屏显示器，弹幕会同步显示在所有选中的屏幕。弹幕窗口只显示聊天正文，使用透明、置顶和鼠标穿透窗口，
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
