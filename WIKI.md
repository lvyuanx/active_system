# 项目知识

## 架构概览

项目采用 Monorepo，包含一个 FastAPI 模块化单体后端和三个 Vue 3 前端应用：Element Plus 管理端、ECharts 大屏端、Vant 4 用户端。

## 数据隔离

活动业务数据通过 `activity_id` 进行隔离。所有活动相关查询和写入都必须携带活动上下文。

## 管理员认证与活动生命周期

管理端使用 HS256 JWT Bearer Token，登录接口只允许 `is_superuser` 用户成功。超级用户由环境变量初始化，密码使用 PBKDF2 哈希保存。活动状态为 `closed`、`open`、`ended`，状态转换由后端校验：`closed <-> open` 可反复切换，非结束状态可手动转为 `ended`，结束后不可恢复。

## 本地端口

- FastAPI：8000
- 管理端：5173
- 大屏端：5174
- 用户端：5175
