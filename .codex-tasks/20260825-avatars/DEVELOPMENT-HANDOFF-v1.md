任务：
T3｜活动用户 SVG 头像与首次登录随机分配

输入版本：
TASK-v2；方案 ARCHITECTURE-v1；WorkPackage `wp-avatar-development`；输入快照 `bc5ef243f7c8076ff521ac75aa9d4524ec49dcf5-a4d99b23e2ea9af723b0892b59adccd6cc6ec488c6d092b10b7d1831cde95a29`。

状态：completed

结论：
头像功能已在主工作树完成串行集成：后端注册事务内分配头像、登录和 `/me` 对历史空值惰性补齐，前端固定映射十款 SVG 并在首页/“我的”展示。既有聊天室代码未被本次头像逻辑修改。

证据：

- `apps/backend/app/core/database.py`：新库包含可空 `avatar_id`，旧库通过 `PRAGMA table_info` + `ALTER TABLE` 兼容升级。
- `apps/backend/app/modules/participants/avatar.py`：头像 ID 限制为 1–10，使用 `secrets.randbelow`；空值使用 `avatar_id IS NULL` 条件更新，并兼容并发请求读取已落库值。
- `apps/backend/app/modules/participants/router.py`：注册、登录、`/me` 的 `ActivityUserResponse` 统一返回 `avatar_id`；分配失败不会返回空头像。
- `apps/backend/tests/test_activity_avatars.py`：覆盖注册、稳定登录/`/me`、活动隔离、错误登录不补齐、旧库迁移与惰性补齐。
- `apps/user-web/src/assets/avatars/avatar-01.svg` 至 `avatar-10.svg`：恰好十个无脚本、无外链的静态 SVG，SHA-256 无重复。
- `apps/user-web/src/components/ActivityAvatar.vue`：仅通过固定 `ActivityAvatarId` 映射本地静态资源，不使用 `v-html` 或用户路径。
- `apps/user-web/src/views/activity/home.vue`、`me.vue` 与 `activity.css`：头像在活动首页和“我的”页展示，保留移动安全区和断点布局。
- `python -m pytest -q apps/backend`：22 passed，退出码 0；仅有既有 FastAPI 弃用警告。
- `pnpm typecheck`：三个前端 typecheck 通过，退出码 0。
- `pnpm build`：三个前端生产构建通过，退出码 0；仅有既有 Rollup 注释和 chunk 大小警告。
- 浏览器视觉核验：390px 与 320px 视口中 `scrollWidth` 等于视口宽度，首页和“我的”均显示头像；退出码不适用于浏览器操作，截图证据保留在本轮工具结果。
- SVG 静态扫描：`COUNT=10`、`DUPLICATE_HASH_GROUPS=0`、`INVALID_STATIC_ASSETS=0`。

变更文件：

`apps/backend/app/core/database.py`、`apps/backend/app/modules/participants/AGENTS.md`、`apps/backend/app/modules/participants/avatar.py`、`apps/backend/app/modules/participants/router.py`、`apps/backend/tests/test_activity_avatars.py`、`apps/user-web/src/api/client.ts`、`apps/user-web/src/assets/avatars/avatar-01.svg` 至 `avatar-10.svg`、`apps/user-web/src/components/ActivityAvatar.vue`、`apps/user-web/src/views/activity/home.vue`、`apps/user-web/src/views/activity/me.vue`、`apps/user-web/src/views/activity/activity.css`、`apps/backend/AGENTS.md`、`apps/user-web/AGENTS.md`、`README.md`、`MEMORY.md`、`LEARNING.md`、`WIKI.md`。

风险或阻塞：

- 当前主工作树原本含聊天室 dirty 改动，工作包按 `DIRTY_INPUT_UNSAFE` 降级为 `SERIAL_SHARED_WRITE`；本次未回滚或清理这些改动。
- 全量构建保留既有 Rollup 警告；不影响退出码。
- 头像不进入聊天协议，聊天头像需求仍属于非目标。

下一步：

交给测试角色执行独立 AC 回归，再交审核与验收。

包级门禁：

`wp-avatar-development` 的实际文件清单为 26 项，限定范围清单 SHA-256 为 `dffe54d2dc52812bbc1188c4e32f44931d45652eb9203b8ea147c51590c6e329`。主树 HEAD 未漂移，HEAD SHA 为 `bc5ef243f7c8076ff521ac75aa9d4524ec49dcf5`，HEAD tree 为 `1f3a86ae798fd11a6b40f179228177dbe3bf3f7c`。串行集成证据为 `SERIAL-INTEGRATION.md`，不作为补丁文件，当前输出补丁字段为 null。不存在越界写入或补丁冲突。

AC 映射：

- AC-001：十个静态 SVG、重复哈希和静态扫描通过。
- AC-002：ActivityAvatar 与首页/我的布局通过 320px、390px 浏览器检查。
- AC-003～AC-008：头像专项后端测试通过。
- AC-009：全量后端测试、前端 typecheck/build 通过，聊天文件未被头像逻辑修改。
- AC-010：活动隔离和重复身份读取测试通过。

实现偏差：

无。头像归属、惰性补齐、随机重复和展示范围均符合 TASK-v2。
