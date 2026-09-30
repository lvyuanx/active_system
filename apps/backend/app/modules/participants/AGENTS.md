# 活动参与者模块说明

## 模块简介

`apps/backend/app/modules/participants` 负责活动公开信息、活动参与者注册/登录/短信登录、活动身份校验、用户身份头像和管理员参与者管理。

## 主要职责

- 按 `activity_id` 查询活动公开信息并保持活动隔离。
- 创建和校验活动参与者身份，生成带活动上下文的 JWT。
- 通过已核验的手机号验证码登录已有用户，或为新手机号补充姓名后创建活动用户。
- 通过稳定的 `activity_user_id` 支持旧令牌兼容与聊天身份关联。
- 为活动参与者分配和读取 1–20 的 `avatar_id`。
- 为超级用户提供活动隔离的参与者分页列表、用户名/手机号模糊搜索、禁言/解除禁言、停用/恢复和移动端抽奖授权操作。
- 按活动用户保存 `can_mobile_lottery` 权限，供移动端抽奖接口实时校验。

## 目录说明

- `router.py`：活动公开详情、注册、用户名登录、短信登录、`/me` 和活动身份依赖。
- `admin_router.py`：管理员参与者分页/搜索列表和状态操作接口。
- `avatar.py`：头像 ID 范围校验、安全随机分配、空值惰性补齐和并发胜者读取。

## 主要流程

新用户注册时在 `activity_users` 插入事务内生成头像；已有用户登录或访问 `/me` 时，如果头像为空则使用 `avatar_id IS NULL` 条件更新。条件更新竞争失败时读取已经落库的合法值，不覆盖已有分配；仍为空或非法时返回错误。管理员停用用户时只保留用户数据并递增 `session_version`，恢复后必须重新登录；禁言只改变发言权限，不影响登录和聊天历史读取。
短信登录先调用短信模块核验验证码；已有手机号直接签发原活动用户 token，新手机号在未提交姓名时只返回 `needs_name`，提交姓名后才在原有注册事务中创建用户。

## 数据流

认证响应统一返回 `activity_id`、`activity_user_id`、`username`、`joined_at` 和 `avatar_id`。头像归属使用 `(activity_id, activity_user_id)`，不同活动之间不共享分配结果。管理员参与者单项响应返回 `activity_id`、`activity_user_id`、`username`、`phone`、`joined_at`、`is_active`、`is_muted` 和 `can_mobile_lottery`；分页列表额外返回 `items`、`page`、`page_size`、`total` 和 `has_more`。
列表接口支持 `keyword`（匹配用户名或手机号）、`page`（默认 1）和 `page_size`（默认 20，最大 100）查询参数，排序按加入时间和稳定用户 ID 倒序。
短信登录接口为 `/api/v1/activities/{activity_id}/auth/sms-login`，成功响应包含 `needs_name` 和可选的 `user`；已有用户不接受登录请求中的姓名修改。

管理员接口统一使用 `/admin/activities/{activity_id}/participants` 前缀，所有读写都要求超级用户权限并带活动条件；移动端抽奖授权使用
`mobile-lottery/grant` 和 `mobile-lottery/revoke` 操作。

`ActivityUserResponse` 和管理员参与者响应均返回 `can_mobile_lottery`。权限不写入 JWT，管理员取消授权后，用户旧 token 也不能继续调用移动端抽奖接口。

新参与者注册事务只创建 `activity_users` 记录，不预创建每个奖品的名单行；抽奖服务对缺失的 `lottery_prize_entries` 按默认可参加处理。
历史活动的旧 `lottery_entries` 记录由抽奖模块按活动懒迁移到已有奖品，迁移完成后新增奖品不会继承旧标记。

## 迁移与注意事项

`core.database.init_database` 为旧 `activity_users` 表增加可空 `avatar_id`，不批量填充历史用户；初始化使用 SQLite `BEGIN IMMEDIATE` 串行化字段迁移。头像只接受后端生成的 1–20 值，用户端通过固定静态 SVG 映射展示，不接受路径或 HTML。
