# 活动参与者模块说明

## 模块简介

`apps/backend/app/modules/participants` 负责活动公开信息、活动参与者注册/登录、活动身份校验和用户身份头像。

## 主要职责

- 按 `activity_id` 查询活动公开信息并保持活动隔离。
- 创建和校验活动参与者身份，生成带活动上下文的 JWT。
- 通过稳定的 `activity_user_id` 支持旧令牌兼容与聊天身份关联。
- 为活动参与者分配和读取 1–20 的 `avatar_id`。

## 目录说明

- `router.py`：活动公开详情、注册、登录、`/me` 和活动身份依赖。
- `avatar.py`：头像 ID 范围校验、安全随机分配、空值惰性补齐和并发胜者读取。

## 主要流程

新用户注册时在 `activity_users` 插入事务内生成头像；已有用户登录或访问 `/me` 时，如果头像为空则使用 `avatar_id IS NULL` 条件更新。条件更新竞争失败时读取已经落库的合法值，不覆盖已有分配；仍为空或非法时返回错误。

## 数据流

认证响应统一返回 `activity_id`、`activity_user_id`、`username`、`joined_at` 和 `avatar_id`。头像归属使用 `(activity_id, activity_user_id)`，不同活动之间不共享分配结果。

## 迁移与注意事项

`core.database.init_database` 为旧 `activity_users` 表增加可空 `avatar_id`，不批量填充历史用户；初始化使用 SQLite `BEGIN IMMEDIATE` 串行化字段迁移。头像只接受后端生成的 1–20 值，用户端通过固定静态 SVG 映射展示，不接受路径或 HTML。
