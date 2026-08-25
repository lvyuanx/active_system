# 项目知识

## 架构概览

项目采用 Monorepo，包含一个 FastAPI 模块化单体后端和三个 Vue 3 前端应用：Element Plus 管理端、ECharts 大屏端、Vant 4 用户端。

## 数据隔离

活动业务数据通过 `activity_id` 进行隔离。所有活动相关查询和写入都必须携带活动上下文。

## 管理员认证与活动生命周期

管理端使用 HS256 JWT Bearer Token，登录接口只允许 `is_superuser` 用户成功。超级用户由环境变量初始化，密码使用 PBKDF2 哈希保存。活动状态为 `closed`、`open`、`ended`，状态转换由后端校验：`closed <-> open` 可反复切换，非结束状态可手动转为 `ended`，结束后不可恢复。

活动用户存储在 `activity_users` 表中，以 `activity_id` 隔离；同一活动内手机号唯一。用户 JWT 携带活动 ID，用户端按 `active_user_token:{activity_id}` 缓存 token。管理端二维码目标地址使用 `VITE_USER_WEB_BASE_URL` 拼接 `/activity/{activity_id}`。

## 用户端移动端视觉

- 用户端活动入口采用 Vue 3 + Vant 4，认证页保留圆环 A 标识和哑金主操作，登录后页展示活动状态、用户摘要和已有服务入口。
- 活动页视觉规则集中在 apps/user-web/src/views/activity/activity.css 与 activity-auth.css，所有选择器使用活动页命名空间；炭黑和深灰用于层次承载，哑金用于品牌强调，成功和结束状态使用独立状态色。
- 活动入口需要适配 320px 起的移动宽度、短屏和 safe-area inset，动态活动名称、描述和用户名必须允许换行，不得造成横向溢出。

## 本地端口

- FastAPI：8000
- 管理端：5173
- 大屏端：5174
- 用户端：5175

## 启动入口

- Windows 双击 `start.cmd`，或执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`，会分别打开后端和前端窗口。
- 执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1 -Docker` 会通过 Compose 构建并启动全部容器。
