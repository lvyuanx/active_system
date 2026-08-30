任务：实现 TASK-v5 奖品图片上传、持久化、安全访问、管理端交互和大屏展示
输入版本：TASK-v5 + ARCHITECTURE-v5
状态：completed
结论：已完成奖品图片媒体链路，保留现有抽奖、库存、中奖、WS、鉴权和活动隔离语义。
证据：

- 数据库在 `apps/backend/app/core/database.py:48-51,190-210` 增加可空图片字段、旧库迁移和唯一索引。
- 媒体校验、临时分块写入、随机 key、原子落盘和孤儿扫描见
  `apps/backend/app/modules/files/service.py:17-205`。
- 图片上传/替换/删除/管理员读取/公开读取见
  `apps/backend/app/modules/lottery/router.py:72-145` 与 `media_service.py:59-162`。
- 配置、快照和开奖对象带安全 `image_url`/`prize_image_url`，内部 storage key 未进入公开投影。
- 管理端 multipart 请求不会覆盖浏览器 boundary，图片 API 和图片编辑器见
  `apps/admin-web/src/api/client.ts:16-28,275-289`、`PrizeImageEditor.vue`。
- 大屏奖品缩略图、中奖图片及加载失败回退见
  `apps/screen-web/src/components/lottery/LotteryScreen.vue:26-76,124-136`。
- `python -m pytest -q apps/backend/tests/test_lottery.py apps/backend/tests/test_lottery_images.py`：退出码 0，18 passed；
  覆盖 DecompressionBombError 拒绝、图片 POST/DELETE 后公开 WS 配置广播、清理保护及配置删除媒体回收。
- `python -m pytest -q apps/backend/tests/test_lottery.py apps/backend/tests/test_lottery_images.py`：退出码 0，19 passed；覆盖配置及奖项级联删除媒体回收。
- `python -m pytest -q apps/backend/tests`：退出码 0，55 passed，7 warnings。
- `pnpm --filter @active/admin-web typecheck`：退出码 0。
- `pnpm --filter @active/admin-web build`：退出码 0。
- `pnpm --filter @active/admin-web test:lottery-image-race`：退出码 0，保存态、刷新版本号和成功后刷新保护断言通过。
- 浏览器验收发现的图片保存竞态已修复：`index.vue` 保存期间丢弃配置刷新，并用版本号阻止早期 GET 回写；
  图片操作成功后在保存态内按需读取最新配置。
- 预审回退修复：Pillow 炸弹尺寸会转为明确图片校验错误；配置后的媒体扫描恢复 300 秒保护窗口；
  图片上传/删除失败会恢复 pending File 或移除标记，支持再次保存重试。
- AC-513 回退修复：配置删除奖品前收集其旧 `image_storage_key`，事务提交后立即清理确定无引用的文件，
  再执行带保护窗口的孤儿扫描；中奖记录阻止删除时事务回滚且媒体保留，见
  `apps/backend/app/modules/lottery/service.py:152-255`。
- 配置删除媒体回归见 `apps/backend/tests/test_lottery_images.py:310-388`，覆盖成功删除和中奖记录阻止删除。
- 奖项级联删除媒体回归见 `apps/backend/tests/test_lottery_images.py`，覆盖级联成功回收；事务失败仍由中奖记录回归覆盖。
- 公开图片路由 `v` 必填并严格匹配当前 `image_id`，无版本请求返回 422，见
  `apps/backend/app/modules/lottery/router.py:140-159` 与图片回归测试。
- 审核回退修复：图片 POST/DELETE 与配置、开奖共用操作锁，数据库提交后广播安全
  `lottery.config.updated`，公开大屏可实时收到图片绑定和移除状态。
- `pnpm --filter @active/screen-web typecheck`：退出码 0。
- `pnpm --filter @active/screen-web build`：退出码 0。
- `pnpm --filter @active/screen-web test`：退出码 0，消息顺序、调度、布局和 lottery-order 测试通过。
- `git diff --check`：退出码 0；代码文件均少于 500 行，新增文件无超过 120 字符行。
变更文件：

- 后端：`apps/backend/app/core/config.py`、`apps/backend/app/core/database.py`、`apps/backend/app/main.py`、
  `apps/backend/pyproject.toml`、
  `app/modules/files/`、`app/modules/lottery/`、`tests/test_lottery_images.py`。
- 管理端：`src/api/client.ts`、`src/views/lottery/index.vue`、`PrizeImageEditor.vue`、
  `lottery-image-actions.ts`、`lottery-config-form.ts`、`lottery.css`、
  `scripts/test-lottery-image-race.mjs`、`package.json`。
- 大屏：`src/api/client.ts`、`src/components/lottery/LotteryScreen.vue`、`LotteryScreen.css`、
  `LotteryScreenImages.css`。
- 部署：`.env.example`、`deploy/compose/docker-compose.yml`、`deploy/nginx/default.conf`。
- 文档：相关模块 `AGENTS.md`、`README.md`、`MEMORY.md`、`LEARNING.md`、`WIKI.md`。
风险或阻塞：无开发阻塞。工作树包含 TASK-v1~v4 和其它用户未提交改动，本次未回退、清理或提交它们。
未执行浏览器视觉验收，实际设备图片加载回退、safe-area 和管理端交互仍需 tester/验收阶段确认。
下一步：进入测试、审核和验收阶段，重点覆盖跨活动访问、公开快照裁剪、替换旧 URL 404、清理重试和浏览器交互。

## 实现摘要

- `MEDIA_ROOT` 默认 `./data/media`，Docker 使用 `active-media` 持久化卷，Nginx 允许至少 6 MiB 请求体。
- 仅接受 JPEG、PNG、WebP；扩展名、声明 MIME、Pillow 真实格式和 5 MiB 上限同时校验。
- 文件先写 `.tmp`，验证后以 UUID key 原子移动；替换/移除在数据库提交后清理旧文件。
- 管理端先保存奖品 JSON，再按待保存状态调用 multipart 图片接口；未保存奖品不会上传图片。
- 保存期间忽略 WebSocket 自发配置刷新，并用版本号阻止早期 GET 覆盖图片上传后的本地状态。
- 大屏只解析安全相对 URL；无图、404 或 `error` 时隐藏图片并保留奖品名称、库存和中奖动画。

## 技术决策

- 继续使用既有 `files/service.py` 和 `lottery/media_service.py`，保持单一媒体实现；未引入重复存储模块。
- 图片引用只由 `activity_id + prize_id + image_id` 生成，公开读取再次校验当前绑定，旧版本统一 404。
- 业务数据库和文件系统不做伪事务：绑定提交成功后清理旧文件，启动/配置操作扫描孤儿作为补偿。
- 配置 PUT 保持纯 JSON，前端请求封装仅在 FormData 时移除 JSON Content-Type。

## AC 映射

- AC-501/502：管理端图片选择、预览、待保存和配置后图片持久化；后端配置响应返回安全 URL。
- AC-503/504：独立替换/删除接口提交后清理旧文件，旧 URL 404，奖品和中奖数据不变。
- AC-505：图片字段可空，既有无图配置、开奖和大屏结构保持兼容。
- AC-506/507：真实 MIME/扩展名、Pillow 解码和 5 MiB 分块上限拒绝非法或超大文件。
- AC-508：数据库绑定在上传验证和原子落盘后更新；失败回滚绑定并清理新文件，原图保持不变。
- AC-509/510：管理接口统一 `require_superuser`，SQL 同时校验活动和奖品归属；公开接口只读当前绑定。
- AC-511/512：公开快照和开奖事件只携带安全图片引用，大屏实现缩略图、中奖图和失败回退。
- AC-513：替换、移除、配置删除、启动和操作后执行文件清理；清理失败记录日志并可重试。
- AC-514：既有 lottery 配置、库存、幂等、名单、WS 事件和大屏顺序测试保持通过。
- 竞态/广播回归：`test_lottery_images.py` 验证上传和删除后公开 lottery WS 收到最新安全配置事件。

## TaskGraph / WorkPackage 证据

- `workflow_id=lottery-v5`、`task_version=TASK-v5`；因主树存在 TASK-v1~v4 及用户改动，
  `effective_mode=SERIAL_SHARED_WRITE`，降级原因 `DIRTY_INPUT_UNSAFE` / `PARENT_PERMISSION_UNAVAILABLE`。
- 唯一开发工作包 `lottery-v5-backend-frontend` 已完成生产代码、测试和文档写入；未执行 Git 元数据操作。
- 配置删除媒体、奖项级联删除与 public `v` 必填回归均在图片测试中；全量后端测试退出码 0，55 passed。

## 方案偏差与残余风险

- 方案无行为偏差；未修改 `router/index.ts`、抽奖协议核心字段或库存计算。
- 开发阶段未运行长期服务和浏览器验收；需后续确认真实浏览器的 multipart 上传、图片跨端 URL 和加载失败回退。
