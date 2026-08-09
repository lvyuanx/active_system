# 项目约束

## 技术架构

- Monorepo 使用 pnpm 管理三个 Vue 前端应用。
- 后端使用 FastAPI 模块化单体。
- 管理端使用 Vue 3 + Element Plus，大屏端使用 Vue 3 + ECharts，用户端使用 Vue 3 + Vant 4。
- 不创建 `packages/` 共享业务包；前端 API 类型按应用分别生成。

## 数据隔离

活动业务数据统一使用 `activity_id` 隔离。新增活动相关表、接口或查询时，必须明确活动上下文和跨活动访问权限。

