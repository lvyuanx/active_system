任务：T3 最终只读审核，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：CHANGES_REQUIRED
证据：WORKPACKAGE-v7 的 46 项 SHA-256、WORKPACKAGE-v6 的 6 项实际文件及三个 NSIS 产物复核匹配；当前代码审查发现 AC-008 阻断、托盘退出阻断和入口参数一致性问题。
变更文件：无
风险或阻塞：实时补齐信号集合无界；启动过弹幕后托盘退出可能被 launcher close 处理器拦截；screen-web 使用参数存在性而非严格值 1；任务图图校验证据仍写 6/6，且审核批次缺少权限屏障事件。
下一步：回退开发修复并补充测试，重新执行受影响测试、审核和验收；不得直接进入 acceptance。

## 审核发现

### 高优先级：AC-008 实时补齐信号无界

apps/screen-web/src/components/realtime/DanmakuOverlay.vue 的 pendingRealtimeMessages 是无界 Map。
HTTP 补齐持续失败时，每个 WebSocket 事件都会追加一项；第 103 行的 200 条限制只作用于
pendingMessages 渲染队列，不能限制该信号集合。连续超过 200 条事件会持续占用内存。

修复要求：将实时信号改为有界 ID 集合或最高水位；超过上限丢弃最旧信号但保留恢复触发能力，
并用自动化测试覆盖超过 200 条信号以及 HTTP 恢复后从游标补齐的行为。

### 高优先级：托盘退出可能失效

apps/danmaku-desktop/src/main.ts 的 launcher close 处理器在 runtime 存在且 isQuitting 为 false 时
取消关闭；托盘菜单直接调用 app.quit()，而 isQuitting 直到 will-quit 才设置。启动过弹幕后点击托盘
退出可能先触发 launcher close 并被取消，导致进程无法正常退出。

修复要求：在 before-quit 设置 isQuitting，保留 will-quit 的快捷键清理，并补充静态或可测证据。

### 中优先级：入口参数与文档不一致

apps/screen-web/src/App.vue 使用 URLSearchParams.has("danmaku-overlay")，因此
danmaku-overlay=0 或 false 也进入弹幕入口；README 和 WIKI 约定只有 danmaku-overlay=1 才进入。

修复要求：严格比较 get("danmaku-overlay") === "1"，并覆盖无参数、0、false、1 的入口判断。

## 其他审核结论

- 后端活动隔离、配置校验、HMAC token 轮换、摘要消息和实时设置推送证据通过。
- Electron 透明、无框、置顶、不可聚焦、鼠标穿透、显示器选择和 sandbox/contextIsolation 边界通过静态审查；
  Windows 实机 UI、鼠标、多显示器移除、托盘交互和真实网络故障本轮未重跑，属于覆盖缺口。
- 模块 AGENTS、README、WIKI、MEMORY 和 CLAUDE 已同步到修复前设计，但修复完成后需复核 screen-web
  与 danmaku-desktop 模块说明。

## 工作流证据问题

- TASKGRAPH-v1.json 的 GRAPH_VALIDATED 事件原文仍为 6/6，而当前图有 8 个节点，需改为 8/8。
- 只读审核派生前未能提供硬权限收紧证据；记录 PERMISSION_NOT_READONLY，并将修复后的审核批次按串行方式执行，
  不宣称并发只读验证。
- acceptance 在审核失败期间保持 BLOCKED；开发修复和重测后应重新置为可执行状态。
