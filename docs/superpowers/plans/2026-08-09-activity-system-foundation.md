# Activity System Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 搭建可启动的活动系统 Monorepo 基础结构，包含 FastAPI 后端、Element Plus 管理端、ECharts 大屏端和 Vant 4 用户端。

**Architecture:** 使用 `apps/` 管理四个独立应用，不创建 `packages/` 共享包。后端采用 FastAPI 模块化单体；前端使用 pnpm workspace 管理依赖，每个应用独立构建和部署，API 类型预留在各自的 `src/api/generated/`。

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Vue 3, TypeScript, Vite, Element Plus, ECharts, Vant 4, pnpm。

---

### Task 1: 创建根工作区配置

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `scripts/generate-api.ps1`

- [ ] **Step 1: 写入 pnpm workspace 配置**

`pnpm-workspace.yaml` 只包含三个前端应用：

```yaml
packages:
  - "apps/admin-web"
  - "apps/screen-web"
  - "apps/user-web"
```

- [ ] **Step 2: 写入根脚本和忽略规则**

根 `package.json` 提供 `dev:*`、`build:*`、`lint` 脚本；`.gitignore` 忽略 Node、Python、环境变量和构建产物。

- [ ] **Step 3: 写入环境变量模板与 API 生成脚本**

脚本从后端 OpenAPI 地址生成指定前端应用的 `src/api/generated/`，不创建共享包。

- [ ] **Step 4: 验证 YAML 和 JSON 可解析**

运行 `node -e "JSON.parse(require('fs').readFileSync('package.json'))"`，预期无输出且退出码为 0。

### Task 2: 创建 FastAPI 后端骨架

**Files:**
- Create: `apps/backend/app/main.py`
- Create: `apps/backend/app/core/config.py`
- Create: `apps/backend/app/api/router.py`
- Create: `apps/backend/app/api/deps.py`
- Create: `apps/backend/app/modules/*/__init__.py`
- Create: `apps/backend/pyproject.toml`
- Create: `apps/backend/tests/test_health.py`
- Create: `apps/backend/AGENTS.md`

- [ ] **Step 1: 创建应用入口和健康检查接口**

`GET /api/v1/health` 返回 `{ "status": "ok" }`，应用启动时不连接外部数据库。

- [ ] **Step 2: 创建配置、路由和活动上下文依赖占位**

配置从环境变量读取；`get_current_activity_id` 只定义接口边界，当前返回请求头中的活动 ID 或 `None`。

- [ ] **Step 3: 创建业务模块目录**

创建 `auth`、`admin`、`activities`、`participants`、`activity_data`、`dashboard`、`files`、`workers` 模块的初始化文件。

- [ ] **Step 4: 添加后端健康检查测试并运行**

运行 `cd apps/backend; python -m pytest -q`，预期 1 个测试通过。

### Task 3: 创建三个 Vue 应用骨架

**Files:**
- Create: `apps/admin-web/*`
- Create: `apps/screen-web/*`
- Create: `apps/user-web/*`
- Create: 每个应用的 `AGENTS.md`

- [ ] **Step 1: 创建统一的 Vite + Vue + TypeScript 基础文件**

每个应用包含 `index.html`、`vite.config.ts`、`tsconfig.json`、`src/main.ts`、`src/App.vue` 和 `src/styles/index.css`。

- [ ] **Step 2: 配置 UI 依赖**

管理端引入 Element Plus；大屏端引入 ECharts；用户端引入 Vant 4。三端各自维护依赖，不创建共享包。

- [ ] **Step 3: 创建最小可见页面**

三个应用分别显示应用名称和当前基础结构状态，确保启动后页面非空。

- [ ] **Step 4: 为每个应用预留 API、路由、状态目录**

创建 `src/api/generated/`、`src/api/modules/`、`src/router/`、`src/stores/`、`src/views/`、`src/components/`、`src/composables/` 等目录。

### Task 4: 添加部署与项目文档骨架

**Files:**
- Create: `deploy/docker/backend.Dockerfile`
- Create: `deploy/nginx/*.conf`
- Create: `deploy/compose/docker-compose.yml`
- Create: `README.md`
- Modify: `MEMORY.md`
- Modify: `WIKI.md`

- [ ] **Step 1: 添加后端 Dockerfile 和 compose 服务定义**

提供后端、管理端、大屏端、用户端的基础服务定义，端口和环境变量通过模板配置。

- [ ] **Step 2: 添加 Nginx 配置骨架**

为三个前端应用预留独立静态资源入口和 `/api/` 反向代理入口。

- [ ] **Step 3: 更新 README 和项目进度**

记录安装、启动、构建命令及当前基础结构完成状态。

### Task 5: 运行基础验证

- [ ] **Step 1: 安装前端依赖并执行三个应用的构建**

运行 `pnpm install` 和 `pnpm build`，预期三个应用均构建成功。

- [ ] **Step 2: 运行 FastAPI 测试**

运行 `cd apps/backend; python -m pytest -q`，预期健康检查测试通过。

- [ ] **Step 3: 启动后端并验证健康接口**

运行 `uvicorn app.main:app --app-dir apps/backend`，访问 `http://127.0.0.1:8000/api/v1/health`，预期返回 `{"status":"ok"}`。

