# ARCHITECTURE-v1：活动用户 SVG 头像与首次登录随机分配

任务：
T3｜活动用户 SVG 头像与首次登录随机分配

输入版本：
TASK-v2；输入快照见 `INPUT-SNAPSHOT-v1.json`。

状态：completed

结论：
采用活动用户表可空 `avatar_id`、注册事务内安全随机分配、登录和 `/me` 条件惰性补齐，以及前端十个静态 SVG 固定映射；聊天协议保持不变。

证据：
当前模块源码、旧 SQLite 迁移测试、用户端构建和 `TASKGRAPH.json` 的 Kahn 预检/WorkPackage/权限批次记录共同支撑本方案。

变更文件：无

风险或阻塞：
主工作树含既有 dirty 改动，隔离写入降级为 SERIAL_SHARED_WRITE；多进程压力测试属于非阻断残余风险。

下一步：
交给开发节点按 `WORKPACKAGE-development.json` 实现，再由测试、审核和验收节点按 TASK-v2 逐条验证。

## 任务

T3｜活动用户 SVG 头像与首次登录随机分配。

## 输入版本

TASK-v2。已确认当前 HEAD 为 `bc5ef243f7c8076ff521ac75aa9d4524ec49dcf5`，工作树包含既有聊天室未提交改动。

## 状态

completed

## 结论

在活动用户表增加可空 `avatar_id` 字段，使用后端安全随机数在注册成功前分配，并在登录/`/me` 读取既有空值用户时以条件更新惰性补齐。认证响应统一返回 `avatar_id`，用户端通过受信任的十个静态 SVG 资源映射渲染。头像只进入首页和“我的”页，不进入聊天消息或 WebSocket 协议。

## 模块边界

- `apps/backend/app/core/database.py`：新库表结构与既有 SQLite 的可空字段兼容迁移。
- `apps/backend/app/modules/participants/`：头像数量、随机分配、惰性补齐和认证响应字段；所有查询继续带 `activity_id` 与稳定用户 ID。
- `apps/user-web/src/assets/avatars/`：十款无脚本、无外链 SVG 静态资产。
- `apps/user-web/src/components/ActivityAvatar.vue`：头像 ID 到静态资源的唯一映射及尺寸/替代文本封装。
- `apps/user-web/src/views/activity/home.vue`、`me.vue` 与 `activity.css`：身份头像展示和移动端布局。
- 既有 `apps/backend/app/modules/chat/` 与用户端 `chat.vue`：只做回归，不改接口或消息模型。

## 接口与数据流

1. 注册：校验活动存在 → 在同一 SQLite 事务中生成 1–10 的 `avatar_id` 并插入 `activity_users` → 读取用户 → 返回包含头像的认证响应。
2. 登录：校验凭证 → 读取当前活动用户；若 `avatar_id` 为空，使用 `UPDATE ... WHERE avatar_id IS NULL` 竞争安全地补齐 → 返回包含头像的认证响应。
3. `/me`：令牌依赖先按 `activity_id` 与 `activity_user_id` 校验身份，再复用登录响应构造逻辑，空值时惰性补齐。
4. 用户端：认证、缓存 token、首页和“我的”共享同一个 `ActivityUserResponse.avatar_id`；`ActivityAvatar` 将 ID 映射为受信任的静态 SVG。

## 兼容与迁移策略

- 新建表直接包含可空 `avatar_id`。
- `init_database` 检查 `PRAGMA table_info(activity_users)`；旧表缺列时执行 `ALTER TABLE ... ADD COLUMN avatar_id INTEGER`。
- 迁移不为历史用户批量生成头像，保留 `NULL`，仅在下一次成功登录或 `/me` 时补齐。
- 应用层只生成 1–10 的值；响应模型限制范围，避免非法头像 ID 进入前端资源映射。
- 不改变 token claims、聊天表、聊天协议和 `activity_user_id` 语义。

## 安全与性能风险

- 使用 `secrets.randbelow`，不使用可预测的时间或用户信息作为随机种子。
- 所有头像更新按活动 ID 和活动用户 ID 定位，禁止按用户名跨活动写入。
- 头像 SVG 为本地静态文件，不接受用户提交的路径或 HTML，组件不使用 `v-html`。
- 惰性补齐仅多一次短 UPDATE/SELECT；已存在头像只读取，不重复随机。
- 条件更新避免两个并发请求重复覆盖已分配值；若 SQLite 写锁异常则事务整体失败，不返回空头像。

## 回滚与测试重点

- 回滚代码前可保留可空字段，不影响旧查询；若需回滚数据库，优先回滚应用逻辑，不删除字段，避免破坏历史数据。
- 后端覆盖十款范围、重复登录稳定、历史空值登录与 `/me` 惰性补齐、旧库迁移、活动隔离和错误边界。
- 前端执行 `vue-tsc --noEmit` 与 Vite 构建，检查十个 SVG 可加载、资源映射完整、首页/我的渲染。
- 集成回归现有聊天测试、稳定活动用户 ID、跨活动访问和只读状态。

## AC 映射

- AC-001：十个独立 SVG 文件、静态安全扫描、构建加载。
- AC-002：`ActivityAvatar` 与首页/我的 CSS 及 320px/600px 构建检查。
- AC-003/004/005：注册、登录和响应字段测试；注册事务内分配，已有值不替换。
- AC-006/010：`activity_id + activity_user_id` 查询与跨活动回归。
- AC-007：旧表迁移与空头像用户惰性补齐测试。
- AC-008：错误凭证、失效令牌和跨活动令牌不触发头像写入。
- AC-009：现有聊天后端与用户端构建/测试回归。
