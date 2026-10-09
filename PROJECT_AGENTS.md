# 项目约束

## 技术架构

- Monorepo 使用 pnpm 管理三个 Vue 前端应用和一个原生微信小程序用户端。
- 后端使用 FastAPI 模块化单体。
- 管理端使用 Vue 3 + Element Plus，大屏端使用 Vue 3 + ECharts，用户端使用 Vue 3 + Vant 4。
- 微信小程序用户端使用原生 TypeScript、WXML、WXSS 和微信小程序 API，独立维护于 `apps/user-web-wx`。
- 不创建 `packages/` 共享业务包；前端 API 类型按应用分别生成。

## 数据隔离

活动业务数据统一使用 `activity_id` 隔离。新增活动相关表、接口或查询时，必须明确活动上下文和跨活动访问权限。

