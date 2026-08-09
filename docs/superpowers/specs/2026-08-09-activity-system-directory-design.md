# 活动系统 Monorepo 目录设计

## 目标

构建一个基于 FastAPI 和 Vue 3 的活动系统，包含后端管理端、活动大屏端和用户端。多个活动之间通过 `activity_id` 实现业务数据隔离。

## 已确认的架构决策

- 采用 Monorepo，统一管理后端与三个前端应用。
- 后端采用 FastAPI 模块化单体，不在初期拆分微服务。
- 活动业务表统一包含 `activity_id`，所有查询、唯一索引和联合索引都必须考虑活动边界。
- 管理端使用 Vue 3 + Element Plus。
- 大屏端使用 Vue 3 + ECharts。
- 用户端使用 Vue 3 + Vant 4。
- 不设置 `packages/` 共享包目录，三个前端应用保持独立。
- 前端 API 类型由 FastAPI OpenAPI 文档生成，并存放在各自应用的 `src/api/generated/`。

## 目录结构

```text
active-system/
├─ apps/
│  ├─ backend/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ core/
│  │  │  ├─ api/
│  │  │  ├─ modules/
│  │  │  │  ├─ auth/
│  │  │  │  ├─ admin/
│  │  │  │  ├─ activities/
│  │  │  │  ├─ participants/
│  │  │  │  ├─ activity_data/
│  │  │  │  ├─ dashboard/
│  │  │  │  └─ files/
│  │  │  └─ workers/
│  │  ├─ migrations/
│  │  └─ tests/
│  ├─ admin-web/
│  ├─ screen-web/
│  └─ user-web/
├─ deploy/
├─ docs/
├─ scripts/
├─ .env.example
├─ package.json
├─ pnpm-workspace.yaml
├─ README.md
├─ PROJECT_AGENTS.md
├─ MEMORY.md
├─ LEARNING.md
├─ WIKI.md
└─ CLAUDE.md
```

## API 客户端策略

每个前端应用在 `src/api/` 下维护自己的 HTTP 客户端、业务 API 封装和 OpenAPI 生成代码。生成流程由根目录 `scripts/` 统一提供命令，但生成结果不跨应用共享。

## 活动数据隔离

活动、参与者、用户活动数据、签到、奖品和统计等业务表均使用 `activity_id`。FastAPI 通过请求依赖或服务层注入当前活动上下文，并强制所有数据访问带活动条件，避免跨活动读取或写入。

