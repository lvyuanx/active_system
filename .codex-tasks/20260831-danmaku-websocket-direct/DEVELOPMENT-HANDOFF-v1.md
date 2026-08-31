# 开发交接：TASK-v1

任务：
实现 `screen-web` 弹幕 WebSocket 完整消息直达；连续实时消息直接消费完整载荷，ready、断线重连和 ID 缺口保留 HTTP 补齐。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v8`；输入快照 `HEAD-5bc847a-clean-20260831`；HEAD
`5bc847a650a072b8ad13508b27a059983d18b036`。

状态：completed

结论：
开发实现和此前基础验证已完成；attempt=7 已按澄清后的现有聊天游标 API 完成测试稳定性修复和回归，未修改后端生产代码或
WebSocket 协议。恢复完成且消息 ID 连续时，渲染器直接调用 `queueMessage(message)`；乱序、缺口或恢复中事件缓存完整 WebSocket
载荷，按当前游标通过既有 HTTP 接口补齐并去重。

证据：
- `apps/screen-web/src/components/realtime/message-order.ts:14-68` 提供 `direct`/`recover`/`ignore` 路由、完整消息去重缓存、
  连续游标消费和容量上限逻辑。
- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue:248-318` 接入完整 WebSocket 消息；连续路径只调用 `queueMessage`，
  缺口路径才调用 `reconcileRealtimeMessages`，恢复失败保留未解决载荷。
- `apps/screen-web/scripts/test-message-order.mjs:22-193` 覆盖连续 direct、ID 缺口 recover、重复 ignore、乱序连续消费、容量边界、
  ready 游标边界和静态 direct 路径断言。
- `pnpm --filter @active/screen-web test`：退出状态 0，`message-order`、调度器、弹幕布局和抽奖无浏览器测试全部通过。
- `pnpm --filter @active/screen-web typecheck`：退出状态 0。
- `pnpm --filter @active/screen-web build`：退出状态 0，Vite 生产构建完成。
- 首次测试交接记录的空 `dist-test` 测试退出状态 1，原因是三个旧编译产物导入路径；本 attempt 已修正并从空目录重跑退出 0。
- 首次后端全文件测试虽有 7 项断言通过，但默认 lifespan 扫描删除了两项 tracked 媒体文件；本 attempt 已隔离 `media_root`，重跑退出 0
  且媒体状态/哈希未变化。
- `pytest -q apps/backend/tests/test_danmaku.py -k websocket_broadcasts_message_summary_and_live_settings`：退出状态 0，
  `1 passed, 6 deselected`，确认四字段弹幕载荷协议兼容。
- `git show -s --format='%H %T' HEAD`：`5bc847a650a072b8ad13508b27a059983d18b036 ac1cf86d65a128cec4b34dd7ed14732ebf55802c`；
  `git cat-file -p HEAD` 首行同为 `tree ac1cf86d65a128cec4b34dd7ed14732ebf55802c`，与 TaskGraph v3 的
  `input_tree_oid`、`head_sha` 一致。
- TaskGraph v3 的 `input_manifest_sha256` 为
  `b79c0db350c77cc20b4177958c957f4494be5659cc673cce99c3328b95380c36`；
  `INPUT-MANIFEST-v1.json` 的 10 项输入文件逐项 SHA-256 与 HEAD 内容一致，按声明的
  `path<TAB>sha256`、LF 连接算法重算聚合值一致。
- `git diff --check`：退出状态 0；工作树中的既有 `.codex-tasks/20260831-danmaku-websocket-direct/` 文件保留。
- attempt=3 从空 `apps/screen-web/dist-test` 完整重测通过；清理前后工作树状态均未出现 `data/media` 变更，两个 tracked
  媒体文件 SHA-256 保持与 HEAD 一致：`152890d0279948f8893bf4611b9605ec.png` 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，
  `9552dcd9537d4680a78a9fd86c21b0ff.jpg` 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。

变更文件：
- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue`
- `apps/screen-web/src/components/realtime/message-order.ts`
- `apps/screen-web/scripts/test-message-order.mjs`
- `apps/screen-web/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-danmaku-websocket-direct/DEVELOPMENT-HANDOFF-v1.md`
- `apps/screen-web/scripts/test-task-scheduler.mjs`
- `apps/screen-web/scripts/test-danmaku-layout.mjs`
- `apps/screen-web/scripts/test-lottery-order.mjs`
- `apps/backend/tests/test_danmaku.py`

风险或阻塞：
无开发阶段阻塞。全局自增 `message_id` 可能因跨活动消息产生合法跳号，因此高 ID 事件仍保守触发 HTTP 缺口检查；
未新增后端字段，浏览器级实时 WebSocket/HTTP 交错流程仍留待下游测试阶段执行。

下一步：
交由测试阶段按 AC-001 至 AC-006 执行回归并记录缺口，再进入审核和验收。

## 实现摘要

- 将实时缓存从仅保存 ID 改为保存完整 `DanmakuMessage`，容量仍限制 200 条，按 `message_id` 去重并保留最新缓存。
- 新增无浏览器依赖的消息路由纯函数：连续且无恢复挂起为 `direct`，缺口/恢复中为 `recover`，已处理 ID 为 `ignore`。
- 渲染器仅在连续路径直接 `queueMessage`；高 ID 事件进入缓存，HTTP 从 `lastMessageId` 补齐，随后按连续游标消费缓存。
- ready 最大 ID 继续只作为提示，恢复失败不清空已缓存完整载荷，重连后继续从当前游标重试。

## attempt=3 测试失败回退修复

- 修正三个测试脚本与实际 TypeScript 输出目录一致的导入路径：`dist-test/realtime/*` 和 `dist-test/lottery/*`；保留已正确的
  `test-message-order.mjs` 与 `test-lottery-globe.mjs` 路径。
- 为 `apps/backend/tests/test_danmaku.py:20-27` 的 `make_client` 增加 `media_root=str(tmp_path / "media")`，避免测试
  lifespan 扫描仓库 `data/media`。
- 未修改弹幕生产实现、WebSocket 协议、项目知识文档或 `data/media`；临时 `dist-test` 只在清理后由测试命令重建。

## 关键技术决策

- `lastMessageId` 仍只由已入渲染队列的消息推进；WebSocket 高 ID 不再直接推进游标。
- 缓存使用纯数组和 `message_id` 去重，沿用 200 条有界策略；缓存溢出不会改变 HTTP 的 `after_id` 游标。
- `takeContiguousRealtimeMessages` 只消费 `lastMessageId + 1` 开始的连续消息，缺口保持在缓存中等待 HTTP 恢复。
- 通过活动 ID校验隔离来自其他活动的载荷；后端 `manager.py` 和公共协议保持不变。

## 工作包和路径范围

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`。
- 工作流：`WF-20260831-DANMAKU-WEBSOCKET-DIRECT`；工作树：`D:/projects/active_system`。
- 交接声明的 `read_scope`、`write_scope`、`ephemeral_scope` 和资源声明均按 `TASKGRAPH-v1.json` 的 `plan_revision=v3` 执行；实际写入只落在上方
  变更文件，`apps/screen-web/dist-test` 仅作为测试临时输出。
- 当前为共享主工作树 `master`，WorkPackage 明确使用 `SERIAL_SHARED_WRITE`；HEAD 与输入快照一致，未执行 Git 元数据变更、提交、
  推送、分支、worktree、stash、reset 或 clean。

## 包级门禁

- 输入版本门禁：`TASK-v1`、产品交接 `PRODUCT-HANDOFF-v1.md`、首次阻断测试交接和 TaskGraph `plan_revision=v3` 已读取且版本一致。
- 快照门禁：HEAD 为 `5bc847a650a072b8ad13508b27a059983d18b036`，tree 为 `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`；
  与 WorkPackage v3 一致，无 HEAD/tree 漂移证据。
- 输入清单门禁：`INPUT-MANIFEST-v1.json` 的 10 项逐文件输入 SHA-256 与 HEAD 内容一致，聚合值
  `b79c0db350c77cc20b4177958c957f4494be5659cc673cce99c3328b95380c36` 重算一致。
- 范围门禁：实际变更文件均属于 WorkPackage `write_scope`，未修改后端生产代码、协议或其他模块。
- 基础质量门禁：空 `dist-test` 下 screen-web test、typecheck、build、后端全量弹幕测试和 `git diff --check` 均退出 0。
- 开发门禁：实现完成，`apps/screen-web/AGENTS.md`、`MEMORY.md`、`LEARNING.md`、`WIKI.md` 已同步。
- 测试失败回退门禁：旧导入路径和仓库媒体扫描问题已分别通过测试脚本路径修正与隔离 `media_root` 修复。

## 验收标准映射

- AC-001：`getRealtimeMessageDecision` 在 `last + 1` 且无恢复挂起时返回 `direct`；渲染器对应分支直接入队完整载荷。
- AC-002：连续实时批次不进入 `reconcileRealtimeMessages`；纯函数和静态回归覆盖 direct 分支及无信号 HTTP 路径。
- AC-003：高于 `last + 1` 的事件返回 `recover`、保留完整载荷，并由 `reconcileRealtimeMessages` 从 `lastMessageId` 调用 HTTP。
- AC-004：`getReadyRecoveryAfterId` 继续返回当前游标；ready 恢复与重连恢复路径未改变，恢复失败保留缓存。
- AC-005：已处理 ID 返回 `ignore`；缓存按 ID 去重，HTTP/WS 交错时按连续游标消费并保持失败重试语义。
- AC-006：screen-web test/typecheck/build、后端弹幕测试、输入清单复核和模块/项目文档更新均有上述证据。

## 已执行验证

| 命令 | 结果 |
| --- | --- |
| 先验证并删除精确 `D:/projects/active_system/apps/screen-web/dist-test` | 目标路径已验证在工作区内，删除后 `target_exists_after=False` |
| `pnpm --filter @active/screen-web test`（空 `dist-test`） | 退出 0；全部 5 组无浏览器测试通过 |
| `pnpm --filter @active/screen-web typecheck` | 退出 0 |
| `pnpm --filter @active/screen-web build` | 退出 0；Vite 生产构建通过 |
| `pytest -q apps/backend/tests/test_danmaku.py` | 退出 0；7 passed |
| `INPUT-MANIFEST-v1.json` 逐项与聚合 SHA-256 重算 | 退出 0；10 项一致，聚合值一致 |
| `git status --short -- data/media`（清理前/后） | 均无输出；两个媒体文件状态未变 |
| `git diff --check` | 退出 0 |

## 补丁与 SHA-256 证据

实现补丁摘要：移除实时 ID 信号缓存，新增完整载荷路由/有界缓存/连续消费；渲染器连续事件直接入队，缺口事件保留 HTTP
补齐；更新无浏览器测试和 screen-web/项目知识文档。attempt=3 仅修正测试编译产物导入路径和后端测试 `media_root` 隔离。
共享主工作树未生成独立补丁文件，主 Agent 集成前应按 WorkPackage 复核限定范围 diff、实际文件清单和补丁摘要。

本次 attempt=3 修订本交接的快照/输入清单证据、测试失败修复和当前哈希记录；共享主工作树未生成独立补丁文件。当前实现/测试/文档文件 SHA-256：

- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue`：`8D9410EED7032E021EF48017067354B8F96FAFFBED41C41AD9F959029B0F15C3`
- `apps/screen-web/src/components/realtime/message-order.ts`：`319E5DD203D85ED73AC8945F1F8956BF73388B1BE6DDF1CFD2D0289787A82A2A`
- `apps/screen-web/scripts/test-message-order.mjs`：`4F5212FF876E1E3AF5F0F9803E482225211C0842106B1443A90C96680D96FAF6`
- `apps/screen-web/scripts/test-task-scheduler.mjs`：`FE043A35CA527F6943F092DD2EAC9C3C47570EAA3D6A2334F271462D7D78E484`
- `apps/screen-web/scripts/test-danmaku-layout.mjs`：`69A6A8012851FD8C200AB077C66612760EFF84BB937E48EBB273A3914AD946CF`
- `apps/screen-web/scripts/test-lottery-order.mjs`：`F722595ECA0F3BDA7973B010DEF81D0B38D490429B566F127C1C4ABE20AC85D0`
- `apps/backend/tests/test_danmaku.py`：`B9BAE969FC425B54AF58ABE1DA1CB83ABE2535F8B299F1DF44982F6E7AEE0380`
- `apps/screen-web/AGENTS.md`：`5CBF424DD0370616655C1D9F2DD2563ECB03ECE3EB2EA01463E06663B31F8A42`
- `MEMORY.md`：`DAC5871C52922F909FB1CF2E40AB3ED7278B796062E44063A6A7876E47DAC239`
- `LEARNING.md`：`FB64F5F8BF0A5EF2F574539518697B75419214D793231C5E7F38878E8046C7ED`
- `WIKI.md`：`072C23D1C43CA9181FD9FE2280CF0DDBD26F83D6C725E3B84E5372042A421FC8`

本交接文件自身的 SHA-256 由主 Agent 在所有阶段完成后重新计算。

## 与方案的偏差

无行为偏差。实现采用方案允许的纯函数路由和完整消息缓存；未修改后端协议、ready 基线、HTTP 恢复接口、轨道调度或 CSS 动画。

## 残余风险

- 当前测试为无浏览器纯逻辑/静态回归和后端协议回归，尚未在真实 Electron 透明窗口中测量实时 HTTP 请求计数与视觉帧率。
- 全局消息 ID 的合法跨活动跳号仍会产生一次保守 HTTP 检查，这是可靠性优先的既有约束。
- 若 HTTP 长时间不可用，缓存保留最新 200 条，历史缺口仍依赖 `after_id` 重试恢复；游标不会因缓存溢出而跳过消息。
- 后端测试已将媒体扫描隔离到 pytest 临时目录；真实部署中的媒体目录仍由应用 lifespan 负责扫描，未在本任务中改变。

## attempt=4 交付证据整改

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；TaskGraph `plan_revision=v4`；输入版本仍为冻结的 `TASK-v1`。
- 本 attempt 仅修订根 `MEMORY.md` 的当前进度证据，并在本交接追加本节说明；TASK-v1 的可观察行为、生产实现、测试脚本、后端测试资产及其既有测试结果均未修改。
- `MEMORY.md` 现准确记录：实现已完成、testing attempt=2 已完成；首次审核因交付证据不完整为 `CHANGES_REQUIRED`；整改进行中，待复审与验收，未宣称审核或验收通过。
- attempt=4 前一开发线程因平台认证错误两次未执行；该失败未对共享工作树产生写入或改变既有实现、测试资产，本 attempt 仅完成上述进度证据修订。
- WorkPackage 快照复核：工作树 `D:/projects/active_system`，`master` 分支且非 detached HEAD；HEAD/tree 为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`，与 v4 交接一致；`read_scope`、`write_scope`、
  `ephemeral_scope` 和 `main-worktree`、`pnpm-cache` 资源声明均已核对。本 attempt 实际写入仅为本文件与 `MEMORY.md`，均在 WorkPackage `write_scope` 内。
- 未执行 Git 元数据操作、提交、推送、分支、worktree、stash、reset 或 clean；未修改 TaskGraph、生产代码或测试资产。

## attempt=5 交付证据整改

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；TaskGraph `plan_revision=v5`；输入版本仍为冻结的 `TASK-v1`。
- 本 attempt 仅同步根 `MEMORY.md` 的当前测试 attempt 与复审状态；生产实现、测试脚本、后端测试资产及既有行为验证结果均未修改。
- `MEMORY.md` 现准确记录 testing attempt=3 已完成，前两次审核均为 `CHANGES_REQUIRED`；当前正在修正真实事件链，待第三次复审与验收，未宣称审核或验收通过。
- TaskGraph 的真实事件链修正由主 Agent 完成，本 attempt 不修改 TaskGraph；本交接仅记录该上游状态，不把事件链修正写成本包的文件变更。
- WorkPackage 快照复核：工作树 `D:/projects/active_system`，`master` 分支且非 detached HEAD；HEAD/tree 为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`，与 v5 交接一致；`read_scope`、`write_scope`、
  `ephemeral_scope` 和 `main-worktree`、`pnpm-cache` 资源声明均已核对。本 attempt 实际写入仅为本文件与 `MEMORY.md`，均在 WorkPackage `write_scope` 内。
- 未执行 Git 元数据操作、提交、推送、分支、worktree、stash、reset 或 clean；未修改 TaskGraph、生产代码或测试资产。

## attempt=6 测试稳定性修复阻断

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；TaskGraph `plan_revision=v6`；输入版本仍为冻结的 `TASK-v1`。
- 失败根因：`apps/backend/tests/test_danmaku.py:529` 的聊天历史默认查询按 `message_id DESC` 返回最新 100 条；并发测试产生超过 100 条消息时，首批测试消息可能被排除，导致 `test_danmaku.py:534` 的首批消息断言不稳定。
- 按冻结任务要求执行的最小修复是将查询改为 `.../chat/messages?after_id=0&limit=100`，未增大上限、未增加 sleep、未放宽断言。
- 该修复首次验证命令 `pytest -q apps/backend/tests/test_danmaku.py::test_admin_danmaku_test_sends_real_chat_messages_to_chat_and_overlay -vv` 退出状态 1；`test_danmaku.py:532` 收到 HTTP 422。现有 `apps/backend/app/modules/chat/router.py:33` 将 `after_id` 声明为 `Query(ge=1)`，因此生产路由拒绝任务要求的 `after_id=0`。
- 生产路由不在本 WorkPackage 写入范围，不能为使测试通过而修改它；按 `HANDOFF_INVALID` 记录方案/范围冲突并停止。目标用例后续两次、后端全量 pytest 和其余要求验证未执行，不得宣称通过。
- 该次测试曾删除仓库 PNG，已从 HEAD 精确恢复；恢复前后 `data/media/lottery-prizes/152890d0279948f8893bf4611b9605ec.png` SHA-256 均为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG 均为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`，最终 `git status --short -- data/media` 无输出。
- 本 attempt 实际修改仅为 `apps/backend/tests/test_danmaku.py` 与本交接文件；未修改生产代码、其他测试/文档、TaskGraph 或媒体最终内容，未执行 Git 元数据操作。

## attempt=7 测试稳定性修复与回归完成

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；TaskGraph `plan_revision=v7`；输入版本仍为冻结的 `TASK-v1`。
- attempt=6 的 `after_id=0` 指令已澄清为主 Agent 的过度具体指令，不属于产品冻结要求；TASK-v1 未升级，本 attempt 改用现有 `before_id` API，不修改生产路由。
- 最小修复：在 `apps/backend/tests/test_danmaku.py:529` 使用安全变量
  `chat_before_id = second_chat["message"]["message_id"] + 1`，请求
  `before_id={chat_before_id}&limit=100`；保留 `first_chat`/`second_chat` ID 断言，不增大上限、不增加 sleep、不放宽断言。
- 预检查阶段发现运行前 PNG 已缺失，按媒体门禁立即停止；随后从 HEAD 精确恢复并建立干净基线。该预检查不计入正式 5 次目标运行。

### 正式验证结果

| 批次 | 命令 | 结果 | 媒体门禁 |
| --- | --- | --- | --- |
| 目标 1 | `pytest -q apps/backend/tests/test_danmaku.py::test_admin_danmaku_test_sends_real_chat_messages_to_chat_and_overlay` | 退出 0；`1 passed in 1.03s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 目标 2 | 同上 | 退出 0；`1 passed in 0.98s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 目标 3 | 同上 | 退出 0；`1 passed in 2.63s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 目标 4 | 同上 | 退出 0；`1 passed in 2.60s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 目标 5 | 同上 | 退出 0；`1 passed in 1.20s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 全量 1 | `pytest -q apps/backend/tests/test_danmaku.py` | 退出 0；`7 passed in 2.20s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |
| 全量 2 | `pytest -q apps/backend/tests/test_danmaku.py` | 退出 0；`7 passed in 2.18s` | 前后 `status` 无输出，PNG/JPG 哈希不变 |

- 七次正式运行均以干净媒体基线开始并完成前后核对。PNG
  `data/media/lottery-prizes/152890d0279948f8893bf4611b9605ec.png` 的 SHA-256 始终为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`；JPG
  `data/media/lottery-prizes/9552dcd9537d4680a78a9fd86c21b0ff.jpg` 始终为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。
- `git diff --check`：退出状态 0。TaskGraph、生产代码、其他测试/文档和 Git 元数据未修改；本 attempt 实际写入仅为
  `apps/backend/tests/test_danmaku.py` 与本交接文件。

### attempt=7 AC-006 映射与残余风险

- AC-006：目标用例连续 5 次、后端弹幕测试全文件 2 次均通过，覆盖媒体状态/哈希门禁；测试修复仅使用现有 `before_id` API，PASS。
- AC-001 至 AC-005 的生产行为和既有 screen-web 验证未改变，沿用之前交接证据，PASS。
- 真实 Electron 透明窗口、桌面预加载桥接、运行时 WS/HTTP 请求计数和视觉帧率仍未覆盖；这些不属于本 attempt 的测试范围。

## attempt=8 最终状态证据同步

- WorkPackage：`WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；TaskGraph `plan_revision=v8`；输入版本仍为冻结的 `TASK-v1`。
- 本 attempt 仅将根 `MEMORY.md` 同步为稳定的最终进度表述：WebSocket 直达实现完成，screen-web test/typecheck/build、目标稳定性重复测试和后端全文件重复回归均通过；两次审核的证据问题及测试不稳定性已整改；当前待第三次复审与验收，未宣称审核通过。
- 本 attempt 未修改生产实现或测试资产；attempt=7 已验证的行为与回归结果保持不变，本次不重复运行测试。
- TaskGraph v8 已由主 Agent 清理重复 JSON `started_at` 键；本 attempt 不修改 TaskGraph，仅在交接中记录该上游状态。
- WorkPackage 快照复核：工作树 `D:/projects/active_system`，`master` 分支且非 detached HEAD；HEAD/tree 为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`，与 v8 交接一致；`read_scope`、`write_scope`、
  `ephemeral_scope` 和 `main-worktree`、`pnpm-cache` 资源声明均已核对。本 attempt 实际写入仅为本文件与 `MEMORY.md`，均在 WorkPackage `write_scope` 内。
- 未执行 Git 元数据操作、提交、推送、分支、worktree、stash、reset 或 clean；未修改 TaskGraph、生产代码、测试资产或其他文档。
