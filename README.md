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
