# 后端模块说明

## 模块简介

`apps/backend` 是活动系统的 FastAPI 模块化单体后端，负责管理活动、用户参与、活动数据和大屏统计。

## 目录职责

- `app/core/`：配置、基础设施和横切能力。
- `app/api/`：路由注册和请求依赖。
- `app/modules/`：按业务领域拆分的后端模块。
- `migrations/`：数据库迁移文件。
- `tests/`：后端自动化测试。

## 数据隔离

活动业务数据必须携带 `activity_id`。服务层和数据访问层需要校验当前活动上下文，禁止跨活动查询或写入。

## 当前已实现模块

- `app/core/database.py`：SQLite 连接、事务和表结构初始化。
- `app/core/security.py`：PBKDF2 密码哈希和 HS256 JWT。
- `app/modules/auth/router.py`：超级用户初始化、登录和管理员权限依赖。
- `app/modules/activities/router.py`：活动 CRUD 列表、创建和生命周期状态转换接口。
- `app/modules/participants/router.py`：活动公开详情、活动用户注册/登录、token 校验和用户身份接口。
- `app/modules/participants/admin_router.py`：超级用户使用的参与者列表、禁言/解除禁言和停用/恢复接口。
- `app/modules/participants/avatar.py`：活动用户头像范围校验、安全随机分配和空值惰性补齐。
- `app/modules/chat/`：活动聊天室历史消息、游标查询、WebSocket 认证和广播。
- `app/modules/danmaku/`：活动弹幕配置、版本化 HMAC token、只读会话和独立实时广播。
- `app/modules/files/`：奖品图片临时存储、真实 MIME 校验、随机 key、原子落盘和孤儿清理；根目录由 `MEDIA_ROOT` 配置。
- `app/modules/lottery/`：活动抽奖配置、按奖品隔离的分页名单和单行规则更新、事务开奖、request_id 幂等、管理员/公开 WebSocket 和安全快照广播；图片变更提交后广播最新安全配置。

## 活动状态

活动新建为 `closed`，可在 `closed` 与 `open` 之间反复切换；管理员可从任一非 `ended` 状态手动结束活动，`ended` 不允许再次开启或关闭。活动接口均要求超级用户 Bearer Token。

活动参与用户存储在 `activity_users` 表中，手机号仅在同一 `activity_id` 内唯一。`is_active` 控制活动身份是否可用，`is_muted` 只限制聊天发言，`session_version` 用于停用时撤销已有活动用户 token。活动用户 JWT 携带 `activity_id`、稳定用户 ID 和会话版本 claim，活动用户依赖会拒绝跨活动访问或使用旧会话；管理员 JWT 不携带这些 claim，保持原有认证兼容性。

活动用户的 `avatar_id` 按 `activity_id + activity_user_id` 隔离，取值为 1–20。新用户在注册事务内分配头像；旧用户保留可空值，仅在成功登录或 `/me` 请求中使用 `avatar_id IS NULL` 条件更新惰性补齐，不执行批量迁移。数据库初始化使用 SQLite `BEGIN IMMEDIATE` 串行化旧表字段迁移；头像分配失败时事务回滚，不返回空头像。

## 配置

通过 `DATABASE_PATH`、`JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`DANMAKU_TOKEN_SECRET`、`LOTTERY_SECURITY_CODE`、
`SUPERUSER_USERNAME` 和 `SUPERUSER_PASSWORD` 配置数据库、令牌、抽奖特殊配置安全码和初始超级用户。
`DANMAKU_TOKEN_SECRET` 为空时回退使用 `JWT_SECRET`；启动时会创建表，并在密码变量非空时初始化或更新超级用户。
