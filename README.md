# 活动系统

基于 FastAPI 和 Vue 3 的多端活动系统 Monorepo，包含：

- `apps/backend`：FastAPI 模块化单体后端。
- `apps/admin-web`：Vue 3 + Element Plus 管理端。
- `apps/screen-web`：Vue 3 + ECharts 活动大屏端。
- `apps/user-web`：Vue 3 + Vant 4 用户端。

## 本地开发

环境要求：Node.js 22+、pnpm 11+、Python 3.11+。

```powershell
pnpm install
python -m pip install -e ".[dev]" --directory apps/backend
uvicorn app.main:app --app-dir apps/backend --reload --port 8000
pnpm dev:admin
pnpm dev:screen
pnpm dev:user
```

本地地址：

- 管理端：http://localhost:5173
- 大屏端：http://localhost:5174
- 用户端：http://localhost:5175
- API 文档：http://localhost:8000/docs

## 管理员活动管理

启动后端前复制 `.env.example` 为 `.env`，设置 `SUPERUSER_USERNAME`、`SUPERUSER_PASSWORD` 和随机的 `JWT_SECRET`。后端首次启动会初始化 SQLite 数据库和超级用户；只有该超级用户可以登录管理端。

登录后默认进入活动选择页。活动状态为“已关闭”“进行中”“已结束”：新建活动默认为已关闭，可在已关闭和进行中之间反复切换；管理员手动结束后不可再次开启或关闭。活动名称必填，描述、开始时间和结束时间可选，若同时填写时间则结束时间必须晚于开始时间。

点击活动卡片进入活动管理页，首页会生成用户端地址和二维码。二维码地址由管理端 `VITE_USER_WEB_BASE_URL` 配置（默认 `http://localhost:5175`）。用户端按活动收集用户名和手机号，手机号在同一活动内唯一；登录 token 按活动 ID 缓存，缓存有效时扫码可直接进入活动首页。

登录活动后，用户端底部提供“首页 / 聊天 / 我的”三个入口。每个活动自动拥有聊天室：`open` 活动可发送
1–500 字符纯文本，`closed` 或 `ended` 活动可查看历史但只读。聊天消息通过 HTTP 游标接口读取，并使用
首帧认证的 WebSocket 实时广播；Nginx 已配置 WebSocket Upgrade。

活动用户注册成功时会从二十款炭黑/哑金卡通 SVG 头像中随机分配一款；头像按活动和活动用户独立保存。
历史用户在成功登录或调用 `/me` 时惰性补齐。聊天页采用微信式消息行：头像、真实用户名、时间和气泡按发送者左右对齐展示；
消息行头像使用稳定的活动用户 ID 做本地映射，不进入聊天消息或 WebSocket 协议。

## 验证

```powershell
pnpm build
python -m pytest -q apps/backend
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
