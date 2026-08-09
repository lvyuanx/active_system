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

