# 验收交接：TASK-v1

任务：
TASK-v1「弹幕 WebSocket 完整消息直达」最终用户场景验收。

输入版本：
`TASK-v1`；TaskGraph `plan_revision=v10`；WorkPackage `WP-20260831-DANMAKU-WEBSOCKET-DIRECT-MAIN`；
输入快照 `HEAD-5bc847a-clean-20260831`；HEAD/tree 为
`5bc847a650a072b8ad13508b27a059983d18b036` / `ac1cf86d65a128cec4b34dd7ed14732ebf55802c`。

状态：completed

结论：
`ACCEPTED`。AC-001 至 AC-006 均达到 TASK-v1 的可观察标准。连续实时弹幕使用 WebSocket 四字段完整载荷直接进入
队列；ready、重连和 ID 缺口继续使用当前游标的 HTTP 恢复；重复、乱序和暂时恢复失败均保留既有可靠性语义。
第三次审核的 `APPROVED` 仅作为审核门禁证据，本验收结论基于以下独立复核，不将审核结论直接等同于验收通过。

证据：
- 已完整读取 `TASK-v1.md`、产品/开发/最新测试交接、首次阻断验收交接、第三次 `APPROVED` 审核交接、输入/输出清单和
  TaskGraph v10；历史两次 `CHANGES_REQUIRED` 交接仍保留。
- `node apps/screen-web/scripts/test-message-order.mjs`：退出 0，输出 `message-order tests passed`；覆盖 direct、recover、
  ignore、连续游标、去重、乱序、失败保留和 200 条缓存边界。
- `node apps/screen-web/scripts/test-task-scheduler.mjs`、`test-danmaku-layout.mjs`、`test-lottery-order.mjs`、
  `test-lottery-globe.mjs`：均退出 0。
- `pnpm --filter @active/screen-web typecheck`：退出 0；`pnpm --filter @active/screen-web build`：退出 0，Vite 生产构建完成。
- `pytest -q apps/backend/tests/test_danmaku.py`：退出 0，`7 passed in 2.29s`；后端弹幕事件仍发送
  `message_id`、`activity_id`、`body`、`created_at` 四字段完整载荷。
- `git diff --check`：退出 0；当前 tracked 改动 11 个，按 v10 `write_scope` 审计 `scope_violations=0`。
- HEAD/tree、输入清单 10 项快照哈希及聚合值 `b79c0db350c77cc20b4177958c957f4494be5659cc673cce99c3328b95380c36` 一致；
  OUTPUT-MANIFEST 当前 SHA-256 为 `f11de04378c713f39646c5d940a6d3fecc10d425cabfed3753b91e7d89a7d966`，其
  21 项 tracked/evidence 文件哈希全部匹配。
- 当前 tracked diff SHA-256 为
  `6549be4ed73e5a9232691c878d30a8ead63ca83e857ab61873935cc0f65807ad`，与 TaskGraph `patch_digest` 和输出清单一致。
- TaskGraph v10 JSON 可解析；事件数 45、原始 `started_at`/`ended_at` 键各 6 次、节点事件引用缺失 0；testing 与 review
  节点为 `SUCCEEDED`，review outcome 为 `APPROVED`，acceptance 在本交接前为 `READY`，cleanup 仍等待验收后执行。
- `git status --short -- data/media` 无输出；PNG SHA-256 为
  `7D043029B4360F7A1C75F5B713BAD6D1ED3783C3E0537908036608157BF2FE90`，JPG SHA-256 为
  `0631AFB49D4B0C3EBDDFCFF945BAC0ED6A39D71EFD3B11008979D9CD00F7FA2E`。

变更文件：无

风险或阻塞：
- 本次浏览器检查打开 `http://localhost:5174/?danmaku-overlay=1`，页面显示“请从 ACTIVE 弹幕桌面工具启动”，
  `window.danmakuDesktop` 为 `false`；因此未将真实 Electron 预加载桥接、运行时 HTTP 请求计数、WS/HTTP 交错时序或视觉帧率
  伪装成已验证。它们是运行时覆盖缺口，不改变本任务已有 AC 的逻辑验收结果。
- WorkPackage 明确采用 `SERIAL_SHARED_WRITE`，`output_patch_path` 与 OUTPUT-MANIFEST 的独立补丁路径均为 `null`，并记录
  `NOT_APPLICABLE` 原因；主树中的当前差异、实际文件清单、patch digest、`git diff --check` 和回归结果已完成一致性复核，未虚构
  不存在的组合补丁或隔离 worktree。
- 全局自增 `message_id` 跨活动产生合法跳号时，客户端会保守执行一次 HTTP 缺口检查；这是任务单明确保留的可靠性策略。

下一步：
由唯一主树集成者在不修改已验收生产行为的前提下完成 cleanup：按 TaskGraph 登记清理或保留临时 `dist-test`，记录最终工作树、
TaskGraph 状态和清理证据；本验收不构成发布批准。

## 验收环境

- Windows PowerShell；Node.js `v22.21.1`；pnpm；Python/pytest。
- screen-web 本地服务端口 5174；后端测试使用 pytest 临时数据库和隔离媒体根目录。
- 主工作树 `D:/projects/active_system`，分支 `master`，WorkPackage 模式 `SERIAL_SHARED_WRITE`。

## 用户场景

- ready 恢复完成后，用户连续发送弹幕，渲染器接收完整 WebSocket 消息并按顺序进入现有滚动队列，不为每条消息发 HTTP。
- 用户在消息缺口或乱序期间发送弹幕，渲染器从当前游标补齐缺失消息，再按 ID 合并展示高 ID 缓存消息。
- 首次连接或重连时，ready 最大 ID 只作为提示，客户端从既有游标恢复，不回放基线之前的历史。
- WebSocket、HTTP 恢复和重连交错或恢复暂时失败时，消息按 ID 去重并保留待恢复正文，成功后继续消费。

## 最终集成证据

- 唯一写入者路径为 `SERIAL_SHARED_WRITE` 主工作树直接集成；无上游 patch SHA、无独立 patch 文件，输出清单和 WorkPackage 均明确
  记录 `output_patch_path=null`、`independent_patch_path=null` 及其 `NOT_APPLICABLE` 原因。
- 主树当前 HEAD/tree 与输入快照一致，tracked diff 文件数为 11，范围审计为 0 越界，实际文件 SHA-256 与 OUTPUT-MANIFEST 21/21 匹配。
- 当前 diff digest `6549be4e...` 与 TaskGraph/OUTPUT-MANIFEST 一致；`git diff --check`、screen-web 构建和后端回归均在当前主树状态
  下完成并通过。
- `git worktree list --porcelain` 仅有登记的主工作树；没有需要清理的隔离 detached worktree。`apps/screen-web/dist-test` 属于登记的
  临时 `ephemeral_scope`，由后续 cleanup 节点处理。

## 每条 AC

- AC-001：`PASS`。`message-order.ts:16-23` 对 `last+1` 且无恢复挂起返回 `direct`；
  `DanmakuOverlay.vue:303-318` 的 direct 分支直接调用 `queueMessage(message)`，独立测试场景展示完整消息一次且未触发恢复。
- AC-002：`PASS`。独立连续 `11/12/13` 场景结果均为 `direct`，展示顺序为 `[11, 12, 13]`，恢复调用计数为 `0`、待处理缓存为空；
  direct 分支静态检查不包含 `reconcileRealtimeMessages` 或 `fetchMessagesAfter`。
- AC-003：`PASS`。独立缺口场景先收到 `12` 返回 `recover`，HTTP 恢复接收 `after_id=10` 返回 `11`，最终按 `[11, 12]` 展示，游标为
  `12`，未跳过 `11`。
- AC-004：`PASS`。`getReadyRecoveryAfterId(100, 999)` 返回 `100`；源码从当前 `lastMessageId` 调用恢复，ready 快照最大 ID 不直接
  推进游标。真实 Electron 重连桥接未覆盖，已列为风险。
- AC-005：`PASS`。重复消息返回 `ignore`；乱序消息按连续游标消费；HTTP 恢复异常后完整 WS 载荷和原游标保留；201 条输入的待恢复缓存
  保留最新 200 条且按 ID 去重；活动 ID 不一致的载荷被过滤。
- AC-006：`PASS`。screen-web 五组无浏览器测试、typecheck、当前生产 build、后端 7 项弹幕协议回归、`git diff --check`、输入/输出
  清单、范围审计、模块/项目文档和媒体门禁均有通过证据。

## 范围偏差

无行为范围偏差。生产实现只修改 screen-web 实时消费逻辑，后端生产 WebSocket 协议和 `/danmaku/messages` 接口保持兼容；测试脚本、
后端测试稳定性修复及 `apps/screen-web/AGENTS.md`、`MEMORY.md`、`LEARNING.md`、`WIKI.md` 均在登记范围内。

## 未验收项

真实 Electron 透明窗口、桌面预加载桥接、运行时 WS/HTTP 请求计数、真实网络交错时序及视觉帧率未验收。它们不属于 TASK-v1
AC-001 至 AC-006 的强制自动化条件，不能被本交接描述为已通过。

## 最终建议

产品验收接受 TASK-v1 的既定行为交付，允许进入 cleanup 门禁；保留上述运行时覆盖缺口和全局 ID 合法跳号风险，不批准发布。
