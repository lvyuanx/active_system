任务：
TASK-v1 独立测试：验证 WebSocket 完整弹幕直达链路。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v8`；WorkPackage `WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；输入快照
`HEAD-5bc847a-clean-20260831`；HEAD `5bc847a650a072b8ad13508b27a059983d18b036`；tree
`ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

状态：completed

结论：
包级测试门禁通过。空 `dist-test` 下 screen-web 五组测试全部真正执行并通过；类型检查、构建、后端弹幕回归和
`git diff --check` 均通过。连续实时消息的 direct 模型恢复调用计数为 0，缺口恢复使用当前游标，重复/乱序/失败
保留及缓存上限均有测试证据。测试前后两个 tracked 媒体文件 SHA-256 未变化，未发现新的越界文件。

证据：
- 初始 `git status --short --branch` 无 `data/media` 变化；HEAD/tree 与 TaskGraph v3 一致。
- 已验证并删除唯一临时目录 `D:/projects/active_system/apps/screen-web/dist-test`，删除后目标不存在。
- `pnpm --filter @active/screen-web test`：退出 0；输出依次包含 `message-order tests passed`、`task-scheduler tests passed`、
  `danmaku layout tests passed`、`lottery order tests passed`、`lottery globe tests passed`。
- `pnpm --filter @active/screen-web typecheck`：退出 0。
- `pnpm --filter @active/screen-web build`：退出 0；Vite 生产构建完成。
- `pytest -q apps/backend/tests/test_danmaku.py`：退出 0；`7 passed in 2.07s`。
- `git diff --check`：退出 0。
- TaskGraph v3 write_scope 与当前 tracked/untracked 文件清单比对：`scope_violations=0`。
- 媒体文件初始/最终 SHA-256 均保持：
  `data/media/lottery-prizes/152890d0279948f8893bf4611b9605ec.png` →
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`；
  `data/media/lottery-prizes/9552dcd9537d4680a78a9fd86c21b0ff.jpg` →
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。

变更文件：
- 本测试阶段允许范围内修改测试资产：`apps/screen-web/scripts/test-message-order.mjs`。
- 本测试阶段新增测试交接：`.codex-tasks/20260831-danmaku-websocket-direct/TESTING-HANDOFF-v1.md`。
- `apps/screen-web/dist-test` 为忽略的临时构建输出。
- 生产源码、后端生产代码、业务文档、TaskGraph 和 Git 元数据未由测试阶段修改。

风险或阻塞：
- 未在真实 Electron 透明窗口中执行 WebSocket/HTTP 请求计数和视觉帧率验证；当前测试为无浏览器纯逻辑与静态回归。
- 浏览器访问 overlay URL 时没有 `window.danmakuDesktop`，只能显示启动占位页，无法注入桌面会话进行端到端验证。
- 全局自增 `message_id` 的跨活动合法跳号仍会保守触发 HTTP 缺口检查，属于任务既有风险。

下一步：
提交审核阶段；审核和用户验收需保留本交接中的逐项证据，不得将纯逻辑测试结果扩大解释为 Electron 视觉流畅性结论。

## 测试环境

- Windows，PowerShell；Node.js `v22.21.1`；pnpm；Python/pytest。
- screen-web 本地服务端口 5174；后端监听 8000、8001。
- WorkPackage 工作树：`D:/projects/active_system`，模式 `SERIAL_SHARED_WRITE`，资源 `main-worktree`、`pnpm-cache`。

## 工作包和路径范围

- 读取范围覆盖 `apps/screen-web/src/components/realtime`、screen-web 测试脚本、后端弹幕管理器与协议测试及项目知识文件。
- 写入范围以 TaskGraph v3 为准；测试阶段实际新增/修改仅限测试脚本、测试交接和 `dist-test` 临时输出。
- `data/media` 不属于写入范围，清理前后状态均无输出。

## 测试用例与 AC 映射

| AC | 用例与证据 | 结果 |
| --- | --- | --- |
| AC-001 | `getRealtimeMessageDecision(10, 11, false)` 返回 `direct`；消费者将完整消息 11 展示并推进游标。 | PASS |
| AC-002 | 连续 11、12、13 均返回 `direct`；`recoveryCallCount === 0`、`recoveryAfterIds === []`；静态检查 direct 分支不含 `reconcileRealtimeMessages` 或 HTTP。 | PASS |
| AC-003 | 先收到 12 返回 `recover`；恢复回调接收 `afterId=10`，返回 11 后按 11、12 展示并清空缓存。 | PASS |
| AC-004 | `getReadyRecoveryAfterId(100, 101/999)` 均返回 100；静态检查 ready 使用当前 `lastMessageId`，不直接使用快照最大 ID。 | PASS |
| AC-005 | 重复消息返回 `ignore`；12、11、13 乱序后按 11、12、13 连续消费；恢复抛错后缓存/游标保留；201 条缓存保留最新 200 条。 | PASS |
| AC-006 | screen-web test/typecheck/build、后端 7 项弹幕测试、输入/范围/哈希审计和测试交接均有证据。 | PASS |

## 逐项结果

- `test-message-order.mjs`：通过，包含 direct 恢复调用计数、当前游标、乱序、重复、失败保留和容量边界断言。
- `test-task-scheduler.mjs`：通过。
- `test-danmaku-layout.mjs`：通过。
- `test-lottery-order.mjs`：通过。
- `test-lottery-globe.mjs`：通过。
- screen-web 类型检查和生产构建：通过。
- 后端 `test_danmaku.py`：7 passed；修复后的临时 `media_root` 未触碰仓库媒体目录。

## 失败复现步骤

本 attempt 未出现阻断失败。历史阻断已由开发修复：旧版本从空 `dist-test` 会因 `test-task-scheduler.mjs` 等脚本引用旧编译路径而
报 `ERR_MODULE_NOT_FOUND`；当前测试脚本路径与 `tsc` 实际输出目录一致，重测已通过。历史后端越界删除已通过临时 `media_root`
隔离修复，当前全量回归后媒体哈希仍一致。

## 回归范围

- WebSocket 完整载荷消息路由纯函数：direct、recover、ignore、连续游标、去重、有界缓存。
- overlay 源码 direct 分支、ready 恢复游标和 HTTP 缺口恢复调用的静态检查。
- 调度器、弹幕布局、抽奖排序和抽奖球体数学回归。
- screen-web 类型检查、Vite 生产构建。
- 后端弹幕 WebSocket/设置/恢复协议测试全文件。
- 未覆盖真实 Electron 桌面预加载桥接、视觉帧率和真实网络计数。

## 包级和集成级门禁

- 输入版本门禁：PASS；TASK-v1、PRODUCT-HANDOFF-v1、TESTING-HANDOFF-v1-BLOCKED.md 修复链和 TaskGraph v4 已核对。
- 快照门禁：PASS；HEAD/tree 与 WorkPackage v3 一致。
- 测试执行门禁：PASS；空 `dist-test` 全量 screen-web 测试五组均执行并通过。
- 质量门禁：PASS；typecheck、build、后端回归、diff check 均退出 0。
- 范围门禁：PASS；TaskGraph v3 write_scope 比对 0 越界，媒体文件前后哈希一致。
- `required_package_barrier`：PASS，测试节点可交付审核节点。
- 集成测试、最终审核和用户验收：尚未由测试角色执行，等待后续节点；不得提前宣称最终交付完成。

## 补丁/文件清单证据

- 未生成独立补丁文件，未执行 commit、push、branch、worktree、stash、reset 或 clean。
- 当前实现/测试/文档文件 SHA-256：
  - `apps/screen-web/src/components/realtime/DanmakuOverlay.vue`：`8D9410EED7032E021EF48017067354B8F96FAFFBED41C41AD9F959029B0F15C3`
  - `apps/screen-web/src/components/realtime/message-order.ts`：`319E5DD203D85ED73AC8945F1F8956BF73388B1BE6DDF1CFD2D0289787A82A2A`
  - `apps/screen-web/scripts/test-message-order.mjs`：`50EAB78909F2E8F393C0C0AB262C28B09CD461F99F1191D141A6F9BBAF609F28`
  - `apps/screen-web/scripts/test-task-scheduler.mjs`：`FE043A35CA527F6943F092DD2EAC9C3C47570EAA3D6A2334F271462D7D78E484`
  - `apps/screen-web/scripts/test-danmaku-layout.mjs`：`69A6A8012851FD8C200AB077C66612760EFF84BB937E48EBB273A3914AD946CF`
  - `apps/screen-web/scripts/test-lottery-order.mjs`：`F722595ECA0F3BDA7973B010DEF81D0B38D490429B566F127C1C4ABE20AC85D0`
  - `apps/backend/tests/test_danmaku.py`：`B9BAE969FC425B54AF58ABE1DA1CB83ABE2535F8B299F1DF44982F6E7AEE0380`
  - `apps/screen-web/AGENTS.md`：`5CBF424DD0370616655C1D9F2DD2563ECB03ECE3EB2EA01463E06663B31F8A42`
  - `MEMORY.md`：`DAC5871C52922F909FB1CF2E40AB3ED7278B796062E44063A6A7876E47DAC239`
  - `LEARNING.md`：`FB64F5F8BF0A5EF2F574539518697B75419214D793231C5E7F38878E8046C7ED`
  - `WIKI.md`：`072C23D1C43CA9181FD9FE2280CF0DDBD26F83D6C725E3B84E5372042A421FC8`
- 实际文件清单（TaskGraph v3 范围内）：上述 11 个 tracked 改动文件，以及 `.codex-tasks/20260831-danmaku-websocket-direct/`
  下的 TASK、产品交接、开发交接、首次阻断交接、输入清单、TaskGraph 和本测试交接；`dist-test` 为忽略临时目录。

## 新增或修改的测试资产

- `apps/screen-web/scripts/test-message-order.mjs`：新增最小消费者模型和恢复调用计数；覆盖 AC-001 至 AC-005，补充 overlay
  direct 分支静态断言。
- `apps/screen-web/dist-test`：由空目录测试命令生成，未纳入版本控制。
- `.codex-tasks/20260831-danmaku-websocket-direct/TESTING-HANDOFF-v1.md`：本测试交接。

## 覆盖缺口

- 无浏览器测试无法观察 Vue 响应式队列和真实 `WebSocket` 事件回调的运行时行为。
- 未在 Electron 透明窗口中记录 `/danmaku/messages` 请求计数、HTTP/WS 交错时序和渲染帧间隔。
- 后端测试验证完整四字段载荷协议，但未替代浏览器端到端链路验证。
- AC-018 不属于 TASK-v1，本工作包无对应峰值线程/隔离写包/队列指标要求。

## attempt=3 重测与交接修正

- 本 attempt 输入版本为冻结的 `TASK-v1`，TaskGraph `plan_revision=v4`；前序线程因平台认证错误两次在执行前失败，未产生共享工作树写入。
- 生产实现、测试脚本和后端测试资产均未修改；`MEMORY.md` 已由前置证据整改修正为“testing attempt=2 已完成、当前待复审与验收”，本测试 attempt 未修改该文件。
- 已将失效交接引用修正为实际存在的 `TESTING-HANDOFF-v1-BLOCKED.md`。

### 测试环境与命令

- Windows PowerShell；Node.js `v22.21.1`；pnpm `11.16.0`；Python `3.11.1`；pytest `8.4.2`。
- `pnpm --filter @active/screen-web test`：退出 0；message-order、task-scheduler、danmaku layout、lottery order、lottery globe 五组测试均通过。
- `pnpm --filter @active/screen-web typecheck`：退出 0。
- `pytest -q apps/backend/tests/test_danmaku.py`：退出 0；`7 passed in 2.52s`。
- `git diff --check`：退出 0；仅有 Git 的 LF/CRLF 提示，无 diff 错误。

### attempt=3 AC 映射

- AC-001：`message-order` direct 连续消息用例通过，完整 WS 载荷直接消费；PASS。
- AC-002：连续消息 direct 用例及恢复调用计数断言通过，恢复调用为 0；PASS。
- AC-003：缺口 recover 用例通过，恢复从当前游标补齐；PASS。
- AC-004：ready/重连游标边界用例通过，ready 快照不直接抬高游标；PASS。
- AC-005：乱序、重复、恢复失败保留和 200 条缓存边界用例通过；PASS。
- AC-006：screen-web 测试、类型检查、后端弹幕协议回归和 diff check 均通过；PASS。

### 工作树、媒体与范围证据

- 测试前后 `git status --short -- data/media` 均无输出；两个 tracked 媒体文件哈希保持不变：PNG
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。
- 测试前后主工作树仍为 `master`、HEAD/tree 为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`；未执行 Git 元数据操作。
- `git diff --name-only` 的 11 个 tracked 改动文件逐项与 TaskGraph v4 `write_scope` 比对，`scope_violations=0`；
  `.codex-tasks/20260831-danmaku-websocket-direct/` 为已声明交接范围，`apps/screen-web/dist-test` 仅为忽略的临时输出。
- 本 attempt 实际修改文件仅为 `.codex-tasks/20260831-danmaku-websocket-direct/TESTING-HANDOFF-v1.md`；生产实现与测试资产文件清单及 SHA-256 未变。

### 门禁与覆盖缺口

- 包级测试门禁：PASS；required testing 节点可向审核交接。集成测试、最终审核和用户验收仍由后续节点负责，未提前宣称完成。
- 真实 Electron 透明窗口、桌面预加载桥接、运行时 WS/HTTP 请求计数、HTTP/WS 交错网络时序和视觉帧率仍未覆盖；纯逻辑测试结果不扩大解释为桌面视觉流畅性结论。
- 本交接文件最终 SHA-256 由主 Agent 在本 attempt 写入完成后重新计算并记录。

## attempt=6 最终证据一致性核验

- 本 attempt 输入版本为冻结的 `TASK-v1`，TaskGraph `plan_revision=v8`；已读取 development attempt=7 交接、更新后的
  `MEMORY.md` 和 v8 TaskGraph。attempt=5 后仅发生 MEMORY、开发交接和 TaskGraph 元数据更新，不重复行为测试。
- `MEMORY.md` 不含具体 testing attempt 编号；相关进度准确记录最新 screen-web test/typecheck/build、目标稳定性重复测试和
  后端全文件重复回归均已通过，当前待第三次复审与验收且未宣称审核通过。

### 一致性检查结果

- `git diff --check`：退出 0；仅有 Git 的 LF/CRLF 提示。
- TaskGraph JSON 解析：通过；原始 JSON 键计数为 `"started_at"=6`、`"ended_at"=6`，每个节点各一组时间键。
- 节点事件引用反向检查：`event_count=37`、`node_event_ref_count=17`、`missing_count=0`；6 个节点的全部引用均存在于
  `events[].event`。
- v8 `git diff --name-only` tracked 改动共 11 个，逐项对当前 `write_scope` 审计为 `scope_violations=0`；HEAD/tree 仍为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

### attempt=5 文件哈希复核

- 生产源码与测试资产共 7 个文件逐项复核，`matched=7/7`：
  - `apps/screen-web/src/components/realtime/DanmakuOverlay.vue`：`8D9410EED7032E021EF48017067354B8F96FAFFBED41C41AD9F959029B0F15C3`
  - `apps/screen-web/src/components/realtime/message-order.ts`：`319E5DD203D85ED73AC8945F1F8956BF73388B1BE6DDF1CFD2D0289787A82A2A`
  - `apps/screen-web/scripts/test-message-order.mjs`：`50EAB78909F2E8F393C0C0AB262C28B09CD461F99F1191D141A6F9BBAF609F28`
  - `apps/screen-web/scripts/test-task-scheduler.mjs`：`FE043A35CA527F6943F092DD2EAC9C3C47570EAA3D6A2334F271462D7D78E484`
  - `apps/screen-web/scripts/test-danmaku-layout.mjs`：`69A6A8012851FD8C200AB077C66612760EFF84BB937E48EBB273A3914AD946CF`
  - `apps/screen-web/scripts/test-lottery-order.mjs`：`F722595ECA0F3BDA7973B010DEF81D0B38D490429B566F127C1C4ABE20AC85D0`
  - `apps/backend/tests/test_danmaku.py`：`87CB5D1DB5F580C9C8CAFDE8C5D98F43B22FC6DFD8B5D3D5314FB99F84403073`

### 媒体、变更与门禁

- 核验前后 `git status --short -- data/media` 均无输出；PNG SHA-256 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG SHA-256 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。
- 本 attempt 未修改生产代码、测试脚本、后端测试资产、业务文档、TaskGraph、媒体或 Git 元数据；仅追加本测试交接。
- 包级测试门禁：PASS；attempt=5 的行为验证结果继续有效。集成测试、第三次复审和用户验收仍待后续节点执行。
- 真实 Electron 透明窗口、桌面预加载桥接、运行时 WS/HTTP 请求计数、交错网络时序和视觉帧率仍为覆盖缺口。
- 本交接文件最终 SHA-256 由主 Agent 在本 attempt 写入完成后重新计算并记录。

## attempt=5 重测与 TaskGraph v7 门禁

- 本 attempt 输入版本为冻结的 `TASK-v1`，TaskGraph `plan_revision=v7`；已完整读取 development attempt=7 交接和 v7 TaskGraph。
- development attempt=7 的测试稳定性修复使用现有 `before_id` 聊天游标 API；本 attempt 未修改生产实现、测试脚本、后端测试资产、
  业务文档、TaskGraph、媒体文件或 Git 元数据，仅追加本测试交接。

### 正式命令结果

- `pnpm --filter @active/screen-web test`：执行 1 次，退出 0；message-order、task-scheduler、danmaku layout、lottery order、
  lottery globe 五组测试全部通过。
- `pnpm --filter @active/screen-web typecheck`：执行 1 次，退出 0。
- `pnpm --filter @active/screen-web build`：执行 1 次，退出 0；Vite 生产构建完成。
- 目标不稳定用例连续 5 次：
  `pytest -q apps/backend/tests/test_danmaku.py::test_admin_danmaku_test_sends_real_chat_messages_to_chat_and_overlay`；
  依次退出 0，耗时 `1.61s`、`1.77s`、`1.13s`、`2.04s`、`1.06s`，每次均 `1 passed`。
- 后端全文件回归连续 3 次：`pytest -q apps/backend/tests/test_danmaku.py`；每次首次即退出 0，依次为
  `7 passed in 1.87s`、`7 passed in 2.96s`、`7 passed in 2.23s`；没有失败后的重跑掩盖。
- `git diff --check`：退出 0；仅有 Git 的 LF/CRLF 提示。

### attempt=5 AC 映射

- AC-001：screen-web message-order direct 连续消息测试通过；PASS。
- AC-002：连续 WS 消息恢复调用计数为 0，screen-web 全量测试通过；PASS。
- AC-003：缺口 recover、当前游标 HTTP 补齐测试通过；PASS。
- AC-004：ready/重连基线游标测试通过；PASS。
- AC-005：乱序、重复、恢复失败保留和缓存边界测试通过；PASS。
- AC-006：screen-web test/typecheck/build、目标用例 5 次、后端全量回归 3 次和 diff check 均通过；PASS。

### TaskGraph 事件与范围核验

- v7 事件引用反向核验：`event_count=34`、`node_event_ref_count=17`、`missing_count=0`；6 个节点的全部引用均存在于
  `events[].event`，`DEPENDENCY_RETRY_PLANNED` 事件数为 0。
- `OUTPUT_MANIFEST_PERSISTED` 保持工作流级事件（`node_id=null`）；`metrics.queued_node_count=0`，当前 `QUEUED` 节点数为 0。
- v7 `git diff --name-only` tracked 改动共 11 个，逐项对 `write_scope` 审计为 `scope_violations=0`；测试前后主工作树仍为
  `master`，HEAD/tree 为 `5bc847a650a072b8ad13508b27a059983d18b036` /
  `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

### 媒体与测试资产证据

- 目标用例 5 次、后端全量 3 次和 build 运行前后，`git status --short -- data/media` 均无输出；PNG SHA-256 始终为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG 始终为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。
- screen-web 测试、类型检查和构建完成后最终媒体状态仍为空；未产生非预期 tracked 文件变化。
- 本 attempt 开始与结束时生产实现和测试资产 SHA-256 未变；当前后端测试资产
  `apps/backend/tests/test_danmaku.py` SHA-256 为 `87CB5D1DB5F580C9C8CAFDE8C5D98F43B22FC6DFD8B5D3D5314FB99F84403073`，
  其余实现/测试文件沿用 v7 开发交接清单。

### 门禁、回归与覆盖缺口

- 包级测试门禁：PASS；目标用例和全文件回归均满足规定的首次通过次数，可交审核。
- 回归覆盖 direct/recover/ignore、连续游标、去重、有界缓存、ready/重连恢复、调度器、弹幕布局、抽奖排序/球体数学、
  screen-web 类型检查/生产构建及后端弹幕协议。
- 未覆盖真实 Electron 透明窗口、桌面预加载桥接、运行时 WS/HTTP 请求计数、HTTP/WS 交错网络时序和视觉帧率；不将纯逻辑
  测试结果扩大解释为桌面视觉流畅性结论。
- 本交接文件最终 SHA-256 由主 Agent 在本 attempt 写入完成后重新计算并记录。

## attempt=4 重测与 TaskGraph v5 事件链核验

- 本 attempt 输入版本为冻结的 `TASK-v1`，TaskGraph `plan_revision=v5`；更新后的开发交接和 `MEMORY.md` 均已读取。
- TaskGraph 已删除不存在的 `DEPENDENCY_RETRY_PLANNED` 引用；事件链中的两个 HTTP 401 替代线程事件均使用
  `PLATFORM_AUTHENTICATION_FAILED`，原始错误保留为执行前 HTTP 401，未伪造容量排队。
- `OUTPUT_MANIFEST_PERSISTED` 已改为工作流级事件（`node_id=null`）；`metrics.queued_node_count=0` 且当前无 `QUEUED` 节点。
- 逐节点 `event_refs` 反向核验命令结果：`plan_revision=v5`、`event_count=27`、`node_event_ref_count=15`、
  `missing_count=0`；6 个节点的全部 15 个引用均可在 `events[].event` 中找到；不存在 `DEPENDENCY_RETRY_PLANNED`。
- `OUTPUT-MANIFEST-v1.json` 当前 SHA-256：
  `C89C9E4C51E0BFE5F3909D92C3073B6A0F678CD529045A0F54F15C8A12B0F30A`。

### attempt=4 命令结果

- `pnpm --filter @active/screen-web test`：退出 0；message-order、task-scheduler、danmaku layout、lottery order、
  lottery globe 五组测试通过。
- `pnpm --filter @active/screen-web typecheck`：退出 0。
- `pytest -q apps/backend/tests/test_danmaku.py`：首次退出 1，`1 failed, 6 passed`；同一命令复跑退出 0，`7 passed in 1.97s`。
- 失败用例单独复跑 `pytest -q apps/backend/tests/test_danmaku.py::test_admin_danmaku_test_sends_real_chat_messages_to_chat_and_overlay -vv`：
  退出 0，`1 passed`。
- `git diff --check`：退出 0；仅有 Git 的 LF/CRLF 提示。

### attempt=4 AC 映射

- AC-001：screen-web direct 消费测试通过；PASS。
- AC-002：连续 WS 消息恢复调用计数为 0；PASS。
- AC-003：缺口 recover 与当前游标 HTTP 补齐测试通过；PASS。
- AC-004：ready/重连基线游标测试通过；PASS。
- AC-005：乱序、重复、失败保留和缓存边界测试通过；PASS。
- AC-006：screen-web 测试/类型检查和 diff check 通过，但后端全量回归首轮失败，当前 attempt 判定 BLOCKED，不能按复跑结果单独放行。

### 失败复现、期望与实际

- 最小复现命令：`pytest -q apps/backend/tests/test_danmaku.py`；首轮失败位置为
  `apps/backend/tests/test_danmaku.py:534`。
- 期望：`first_chat.message_id` 和 `second_chat.message_id` 均出现在活动聊天历史。
- 实际：断言 `assert 1 in {5, 6, 7, 8, 9, 10, ...}` 失败；失败现场临时数据库只读检查显示同一活动已有 104 条聊天消息，
  聊天历史 `limit=100` 返回最新 100 条并从 ID 5 开始，首条 ID 1/2 被排除。
- 影响：后端全量回归对测试时序敏感；单用例及第二次全量复跑通过，仍不能消除首轮失败证据。测试门禁回退开发，需处理该不稳定测试后再重测。

### 工作树、媒体、范围与变更

- 测试前后 `git status --short -- data/media` 均无输出；PNG SHA-256 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。
- 测试前后 HEAD/tree 仍为
  `5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`；
  `git diff --name-only` 的 11 个 tracked 改动文件与 v5 `write_scope` 比对为 `scope_violations=0`。
- 本 attempt 未修改生产实现、测试脚本、后端测试资产、业务文档、TaskGraph、媒体文件或 Git 元数据；仅追加本测试交接。
- 当前 attempt=4 测试状态：`blocked`；包级测试门禁因后端全量回归首轮失败未通过。真实 Electron 网络交错、请求计数和视觉帧率仍为覆盖缺口。
- 本交接文件最终 SHA-256 由主 Agent 在本 attempt 写入完成后重新计算并记录。

## attempt=6 最终结构核验

任务：
TASK-v1 独立测试证据最终结构核验；本 attempt 只核对 v8 TaskGraph、v7 测试结果和范围/哈希证据，不重跑会写入业务数据的 pytest。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v8`；WorkPackage `WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；输入快照
`HEAD-5bc847a-clean-20260831`；HEAD `5bc847a650a072b8ad13508b27a059983d18b036`；tree
`ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

状态：completed

结论：
最终结构、事件链、v7 测试证据、范围和媒体门禁均复核通过，包级测试门禁保持 PASS。v8 仅同步交付元数据，未改变已验证的
生产实现或测试资产；集成测试、第三次复审和用户验收仍由后续节点负责。

证据：
- `TASKGRAPH-v1.json` 可解析，原始 JSON 中 `"started_at"` 键 6 个、`"ended_at"` 键 6 个；development/testing 节点各有一组
  键（testing 当前值为 null，因节点尚未启动），无重复时间键。
- TaskGraph 事件反向核验：`event_count=37`、`node_event_ref_count=17`、`missing_count=0`；无
  `DEPENDENCY_RETRY_PLANNED`。`OUTPUT_MANIFEST_PERSISTED` 事件不含 `node_id` 属性（等价于不存在/null）。两项 raw HTTP 401
  事件 `DEVELOPER_THREAD_REPLACED`、`TESTER_THREAD_REPLACED` 的 `reason_code` 均为
  `PLATFORM_AUTHENTICATION_FAILED`，未伪造容量排队。
- 已读取并复核 v7 testing attempt=5 的原始结果，未重跑：`pnpm --filter @active/screen-web test`、`typecheck`、`build` 各执行
  1 次且首次退出 0；目标用例连续 5 次首次均退出 0；`pytest -q apps/backend/tests/test_danmaku.py` 连续 3 次首次均退出 0，
  分别为 `7 passed in 1.87s`、`7 passed in 2.96s`、`7 passed in 2.23s`。
- v7 记录的 7 个生产源码/测试资产 SHA-256 与当前重算值 `matched=7/7`：
  `DanmakuOverlay.vue=8D9410EED7032E021EF48017067354B8F96FAFFBED41C41AD9F959029B0F15C3`，
  `message-order.ts=319E5DD203D85ED73AC8945F1F8956BF73388B1BE6DDF1CFD2D0289787A82A2A`，
  `test-message-order.mjs=50EAB78909F2E8F393C0C0AB262C28B09CD461F99F1191D141A6F9BBAF609F28`，
  `test-task-scheduler.mjs=FE043A35CA527F6943F092DD2EAC9C3C47570EAA3D6A2334F271462D7D78E484`，
  `test-danmaku-layout.mjs=69A6A8012851FD8C200AB077C66612760EFF84BB937E48EBB273A3914AD946CF`，
  `test-lottery-order.mjs=F722595ECA0F3BDA7973B010DEF81D0B38D490429B566F127C1C4ABE20AC85D0`，
  `test_danmaku.py=87CB5D1DB5F580C9C8CAFDE8C5D98F43B22FC6DFD8B5D3D5314FB99F84403073`。
- `git diff --check` 退出 0。当前 v8 范围审计为 `tracked_changed_count=11`、`untracked_nonignored_count=10`、
  `scope_violations=0`；HEAD/tree 仍为上述输入快照值，分支为 `master`。
- `git status --short -- data/media` 核验前后均无输出；PNG SHA-256 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG SHA-256 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。

变更文件：
本 attempt 仅追加 `.codex-tasks/20260831-danmaku-websocket-direct/TESTING-HANDOFF-v1.md`；未修改生产代码、测试脚本、后端
测试资产、业务文档、TaskGraph、媒体或 Git 元数据。未生成补丁、未执行 commit/push/branch/worktree/stash/reset/clean。

风险或阻塞：
无本 attempt 阻塞。AC-001 至 AC-006 沿用 v7 attempt=5 已通过证据；真实 Electron 透明窗口、桌面预加载桥接、运行时
WS/HTTP 请求计数、HTTP/WS 交错时序和视觉帧率仍未覆盖，不能由无浏览器测试结果推断视觉流畅性。交接文件自身 SHA-256
需在本次追加完成后重新计算并由主 Agent 记录。

下一步：
将本交接交给审核节点；保留 AC 映射和上述证据，等待集成测试、第三次复审与用户验收。

### attempt=6 AC 映射与回归范围

- AC-001：v7 `message-order` direct 连续消息和完整载荷消费证据未受 v8 元数据同步影响，PASS。
- AC-002：v7 连续消息恢复调用计数为 0，screen-web 全量测试首次通过，PASS。
- AC-003：v7 缺口 recover、当前游标 HTTP 补齐和高 ID 缓存证据保持，PASS。
- AC-004：v7 ready/重连基线游标证据保持，PASS。
- AC-005：v7 乱序、重复、恢复失败保留和 200 条缓存边界证据保持，PASS。
- AC-006：v7 screen-web test/typecheck/build、目标用例 5 次、后端全量回归 3 次、`git diff --check`、范围和媒体核验均有
  首次退出 0 或一致性证据，PASS。

### attempt=6 门禁、补丁与覆盖缺口

- 包级测试门禁：PASS；v7 行为测试证据保持，v8 结构核验无失配。
- 集成级门禁：未执行；唯一集成者尚未应用或验证组合补丁，审核与验收未启动。
- 补丁/文件清单：无独立补丁；当前实现/测试资产为上述 `matched=7/7`，v8 工作包 write_scope 审计为 0 越界；TaskGraph
  工作流目录内 10 个未跟踪证据文件均在声明目录范围内。
- 新增或修改的测试资产：无；仅追加本测试交接文件，`apps/screen-web/dist-test` 若存在仍为忽略的临时输出。
- 覆盖缺口：无浏览器运行时 Vue/WebSocket 回调验证，无真实 Electron 网络请求计数、交错恢复时序和渲染帧率验证；后端协议
  测试不能替代桌面端到端链路。

## attempt=8 v10 最终结构修订

任务：
TASK-v1 独立测试最终交接结构核验；本 attempt 仅复核上游修正后的 TaskGraph v10 和既有测试证据，未重跑会写入业务数据的测试。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v10`；WorkPackage `WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；输入快照
`HEAD-5bc847a-clean-20260831`；HEAD/tree 为
`5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

状态：completed

结论：
当前 v10 结构门禁通过。现场 TaskGraph 事件数为 45，事件引用无缺失；输入清单仍按开始快照 entries 重算，当前修改文件仅由
OUTPUT-MANIFEST/actual_file_manifest 验证。此前 v8/v9 的事件计数（包括 37）仅是历史快照，不作为当前结论。

证据：
- TaskGraph JSON 可解析，原始 `"started_at"` 与 `"ended_at"` 键各 6 个；逐节点每个键各出现一次，无重复。
- 当前事件反向核验：`event_count=45`、`node_event_ref_count=24`、`missing_count=0`；缺失引用为 0，
  `DEPENDENCY_RETRY_PLANNED` 数量为 0。
- `OUTPUT_MANIFEST_PERSISTED` 事件不含 `node_id` 属性；两个 raw HTTP 401 替代线程事件的 `reason_code` 均为
  `PLATFORM_AUTHENTICATION_FAILED`。
- `INPUT-MANIFEST-v1.json` 的 10 项 `entries` 按声明的 `path<TAB>sha256` + LF 算法重算为
  `b79c0db350c77cc20b4177958c957f4494be5659cc673cce99c3328b95380c36`，与声明值一致；重算未读取当前工作树文件。
- 当前 TaskGraph `actual_file_manifest` 与 OUTPUT-MANIFEST 的 tracked 文件均为 `11/11` SHA-256 匹配；输出清单 SHA-256 为
  `d3fb08510db6076dc230e171475a0d5a62b674a4147eeca36560a1b70a9b60c1`。
- v7 testing attempt=5 的行为回归证据已复核且未重跑：screen-web `test/typecheck/build` 各首次退出 0；目标用例连续 5 次
  首次退出 0；后端全量回归连续 3 次首次退出 0，分别为 `7 passed in 1.87s`、`7 passed in 2.96s`、`7 passed in 2.23s`。
- `git diff --check` 退出 0；v10 write_scope 审计为 `scope_violations=0`，当前主树仍为 `master` 且 HEAD/tree 与输入快照一致。
- `git status --short -- data/media` 输出为空；PNG SHA-256 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG SHA-256 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。

变更文件：
本 attempt 仅追加 `.codex-tasks/20260831-danmaku-websocket-direct/TESTING-HANDOFF-v1.md`；未修改生产代码、测试脚本、后端
测试资产、TaskGraph、媒体或 Git 元数据，未生成独立补丁。

风险或阻塞：
无本 attempt 阻塞。AC-001 至 AC-006 沿用 attempt=5 行为及回归证据并完成当前结构核验。真实 Electron 透明窗口、桌面预加载
桥接、运行时 WS/HTTP 请求计数、交错恢复时序和视觉帧率仍未覆盖；不能由无浏览器测试推出桌面视觉流畅性。

下一步：
交由后续验收/cleanup 流程；共享主树为 `SERIAL_SHARED_WRITE`，无独立补丁集成节点，cleanup 必须等待验收通过后执行。

### attempt=8 AC 映射与门禁

- AC-001：direct 连续消息完整载荷消费证据沿用 v7，PASS。
- AC-002：连续 WS 消息恢复调用计数为 0，screen-web 全量测试首次通过，PASS。
- AC-003：缺口 recover、当前游标补齐和高 ID 缓存证据沿用 v7，PASS。
- AC-004：ready/重连基线游标证据沿用 v7，PASS。
- AC-005：乱序、重复、恢复失败保留和 200 条缓存边界证据沿用 v7，PASS。
- AC-006：v10 当前事件数 45、引用缺失 0、输入/输出清单语义、11/11 当前文件哈希、scope、媒体和既有回归证据均通过，PASS。

### attempt=8 测试环境、范围与覆盖缺口

- 环境：Windows PowerShell；工作树 `D:/projects/active_system`；`master`；WorkPackage 模式
  `SERIAL_SHARED_WRITE`；资源 `main-worktree`、`pnpm-cache`。
- 范围：读取任务单、验收阻断交接、v10 TaskGraph、输入/输出清单、历史测试交接和当前工作树；本 attempt 写入范围仅本测试交接。
- 回归：复用 attempt=5 的 screen-web 五组无浏览器测试、类型检查、生产构建、目标用例 5 次和后端全量回归 3 次；本次只读
 复核，不重复运行 pytest。
- 包级测试门禁：PASS。集成/最终验收/cleanup 尚未由测试角色执行；真实 Electron 网络和帧率仍为覆盖缺口。
- 交接文件最终 SHA-256 由本次追加完成后重新计算并由主 Agent 记录。
