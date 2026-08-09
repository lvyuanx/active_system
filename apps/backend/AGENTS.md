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

## 活动状态

活动新建为 `closed`，可在 `closed` 与 `open` 之间反复切换；管理员可从任一非 `ended` 状态手动结束活动，`ended` 不允许再次开启或关闭。活动接口均要求超级用户 Bearer Token。

## 配置

通过 `DATABASE_PATH`、`JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`SUPERUSER_USERNAME` 和 `SUPERUSER_PASSWORD` 配置数据库、令牌和初始超级用户。启动时会创建表，并在密码变量非空时初始化或更新超级用户。
