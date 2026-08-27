任务：修复最终审核发现的 AC-008、托盘退出和入口分流问题
输入版本：TASK-v1
状态：completed
结论：WORKPACKAGE-v8 的实现修复、模块说明同步和指定局部验证已完成，开发门禁通过。
证据：三项指定命令均退出 0；输入 HEAD/tree/branch 与 WORKPACKAGE-v8 匹配；授权文件哈希和范围已复核。
变更文件：apps/screen-web/src/App.vue；apps/screen-web/src/components/realtime/DanmakuOverlay.vue；apps/screen-web/src/components/realtime/message-order.ts；apps/screen-web/scripts/test-message-order.mjs；apps/screen-web/AGENTS.md；apps/danmaku-desktop/src/main.ts；apps/danmaku-desktop/AGENTS.md；本文件。
风险或阻塞：本工作包未执行全量构建、NSIS 打包或 Windows UI/托盘实机验证；AC-006、AC-007 和 AC-010 的下游验证仍需执行。
下一步：交由下游测试、重新审核和验收；保留本共享工作树中的既有改动，不提交或修改 Git 元数据。

## 实现摘要

- `apps/screen-web/src/components/realtime/message-order.ts` 新增无浏览器依赖的实时信号纯函数：ID 去重、最多 200 项、有序到达时超限淘汰最早项，并按已处理游标清理已恢复信号。
- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue` 不再保存无界的完整实时消息 `Map`，仅保存有界 ID 信号；HTTP 恢复仍从 `lastMessageId` 调用 `after_id`，因此信号溢出不会跳过中间遗漏消息。
- `apps/screen-web/src/App.vue` 将入口判断改为 `new URLSearchParams(window.location.search).get("danmaku-overlay") === "1"`，未改变 Electron 的 `loadURL/loadFile` 参数。
- `apps/danmaku-desktop/src/main.ts` 在 `before-quit` 设置 `isQuitting`，`will-quit` 仅注销全局快捷键，使托盘退出能够穿过 launcher close handler；停止、恢复和快捷键逻辑保持不变。
- 两个模块 `AGENTS.md` 已补充本次边界队列、入口判断、托盘退出和验证说明。

## 审核问题逐项映射

### AC-008：实时信号有界、去重并保留恢复能力

- `message-order.ts` 的 `addPendingRealtimeSignal` 将信号容量固定为 200；重复 ID 不增加集合长度，加入第 201 项时丢弃最早项并保留最新项。
- `DanmakuOverlay.vue` 的恢复循环仍使用 `fetchMessagesAfter(lastMessageId.value)`，以 HTTP 分页完整拉取游标后的遗漏范围；信号集合只承担触发恢复的作用。
- `scripts/test-message-order.mjs` 覆盖高 ID 乱序、去重、游标边界、100 -> 101 首次 ready 补齐、201 个信号的 200 项边界和四种入口值。

### 托盘退出

- `apps/danmaku-desktop/src/main.ts:293-299` 将 `isQuitting = true` 放在 `before-quit`，`will-quit` 只调用 `globalShortcut.unregisterAll()`。
- `stopOverlay`、`toggleOverlay`、托盘停止/恢复菜单、`Ctrl+Shift+D` 和显示器移除处理未改动其既有职责。

### 入口分流

- `apps/screen-web/src/App.vue:13` 仅当 `danmaku-overlay` 的值严格等于字符串 `1` 时渲染 `DanmakuOverlay`。
- `scripts/test-message-order.mjs` 以无浏览器 `URLSearchParams` 纯逻辑覆盖无参数、`0`、`false` 和 `1`，并静态断言 App.vue 使用严格 `get(...) === "1"`。

## 命令退出码

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `pnpm --filter @active/screen-web test` | 0 | `message-order tests passed`；包含 AC-008 边界与四种入口值测试。 |
| `pnpm --filter @active/screen-web typecheck` | 0 | `vue-tsc --noEmit` 通过。 |
| `pnpm --filter @active/danmaku-desktop typecheck` | 0 | `tsc --noEmit -p tsconfig.json` 通过。 |
| WorkPackage 输入/范围/哈希/代码尺寸复核 PowerShell 命令 | 0 | HEAD/tree/branch 匹配；授权文件存在；代码行宽和文件大小通过。 |

此前一次合并执行的附带行宽诊断因 PowerShell 表达式写法错误退出 1；该命令未写入文件，随后以独立修正命令复核退出 0，非项目验证失败。

## AC-006/AC-007/AC-008/AC-010 映射

| AC | 本工作包结论 | 证据与未覆盖项 |
| --- | --- | --- |
| AC-006 | 保持兼容，局部通过 | `main.ts` 的 token、显示器选择、启动和恢复流程未改变；Electron typecheck 退出 0。未执行 Windows 启动和显示器 UI。 |
| AC-007 | 保持兼容，局部通过 | 透明、无框、置顶、不可聚焦、鼠标穿透配置未改变；Electron typecheck 退出 0。未执行 Windows 鼠标穿透、托盘和快捷键实机验证。 |
| AC-008 | 本工作包通过 | 201 个信号测试保持 200 项、淘汰最早并保留最新；HTTP 补齐继续使用 `lastMessageId/after_id`。未做动画视觉量测。 |
| AC-010 | 仅完成指定局部门禁 | screen-web test/typecheck 与 Electron typecheck 均退出 0；按任务要求未执行全量 `pnpm build`、NSIS 或 Windows UI，因此整体 AC-010 留给下游。 |

## WorkPackage 与路径范围

- 工作包：`main-integration-repair-review`，模式：`SERIAL_SHARED_WRITE`，工作树：`D:\projects\active_system`。
- 输入 HEAD：`4e35b3da19742aff672cdd58910bbf60b8935f59`；输入 tree：`0b0d3e4ed5a85a37eebe3aadf45782feaa8d0fb4`；当前复核均匹配。
- v8 输入清单哈希：`BCD60D1CBFB4655B5850E5261386FFB639714AE8CE4BCC8C06741A4D84F374E6`。
- 本次实际写入文件全部属于 `write_scope`；`dist-test` 属于 `ephemeral_scope`。未修改 `WORKPACKAGE-v8.json`、`TASKGRAPH-v1.json`、`MEMORY.md`、`WIKI.md` 或 `README.md`。
- 工作树在本工作包开始前已存在其他模块的 dirty/untracked 改动；本次保留这些既有改动，未将其作为本工作包变更。

## 包级门禁

- WorkPackage 输入版本、绝对路径、HEAD/tree/branch 和授权模式已核对。
- 实现门禁：通过；三项修复和两个模块说明均已落地。
- 基础验证门禁：通过；指定测试与两项类型检查均退出 0。
- 范围门禁：通过；实际新增/修改集合为 8 个 write_scope 文件，测试产物仅在 ephemeral_scope 内。
- 下游门禁：未宣称通过；完整回归、全量构建、NSIS、Windows UI、复审和验收需由下游执行。

## 当前授权文件 SHA-256

以下为本交接生成前已复核的 7 个输入授权文件最终哈希；本文件哈希由主 Agent 在接收交接后复核。

| 文件 | 输入清单 SHA-256 | 当前 SHA-256 |
| --- | --- | --- |
| `apps/screen-web/src/App.vue` | `32915A1B66E62AF26F2D62ED569A261EF67050DCB2DF332F59AB5965205AF8A2` | `E025BFDD7B773B1D3960D281FE94943676E31A476D31180DBFCFD2691E9BEE48` |
| `apps/screen-web/src/components/realtime/DanmakuOverlay.vue` | `4123F51480F2DAF371A65D35F9356A2DA309EAAC05BEDB7326AB36DC800A3181` | `308F4B5B80D2E35A61C8F81F5FF4D744813F2F673531C81D3AA1618EBBA53DA0` |
| `apps/screen-web/src/components/realtime/message-order.ts` | `FC1E40E7CED9AC858AD3906C9D25BAAA0E660776478A78A562452FCB4AD316AD` | `3E3A66CB86D389A212A2FE2842FD7AAA28DCF9FD217D9C63C9EE97FB5448A47A` |
| `apps/screen-web/scripts/test-message-order.mjs` | `0F207071373C96EE13D25F031221833F66C047FA5C789B4E596CE7A693DCC204` | `FD1A7B41211735F085349769B4BA4D129AB6D5EBAD6CDFE0C2DDE974D2BF2410` |
| `apps/screen-web/AGENTS.md` | `0DDC6D7C9D2D37351538F3C20332C7B0ABC9194F60872076A6349A5D1AFFBDCE` | `4BBC2C96CED2D565936EDBB094A7465FFF26768D80D48F49A4EA2F3EF9D018CF` |
| `apps/danmaku-desktop/src/main.ts` | `5AF146174A3A9FE4B08B257516E96DB3A557DA7E601F6B4183A8C9E36600B11E` | `2E8DEDA849FCA317C1017312F99FCE0CB9FB22BEDFFAC05DB15DB971E13AE8F2` |
| `apps/danmaku-desktop/AGENTS.md` | `69502A5560006BC84EF71C43BFE151386553EF85B1D27DF1ADA3CF17CB699CDE` | `B0611B80F6F68BC103005C68B0FE707B631E1734AFAA6D6028A0EB9F62CE188A` |

## 补丁摘要与残余风险

- 补丁摘要：新增两个有界实时信号纯函数及其测试；将渲染器实时待处理状态从无界消息 Map 改为有界 ID 数组；收紧 screen-web 入口值判断；调整 Electron 退出事件顺序；补充两个模块说明。
- 未执行 Git add、commit、push、branch、worktree、stash、reset 或 clean；未修改 Git 元数据。
- 残余风险：本轮没有真实 HTTP 故障注入、Windows 托盘交互、快捷键、覆盖窗口鼠标穿透、多显示器移除、全量构建或 NSIS；下游应针对这些范围执行回归。
- 方案偏差：无实现方案偏差；按审核要求新增无浏览器纯函数测试，未改变 Electron `loadURL/loadFile` 参数和既有 stop/resume 行为。
