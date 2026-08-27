任务：T3 开发补充交接，活动弹幕桌面悬浮工具
输入版本：TASK-v1
状态：completed
结论：已修复审核发现的普通大屏入口回归，并将弹幕实时事件改为以 WebSocket 为信号、按 after_id 通过 HTTP 有序补齐，避免高消息 ID 先到时跳过较低 ID 消息。
证据：当前实现文件行宽扫描无超过 120 字符的行，代码文件均不超过 500 行；DanmakuOverlay.vue 通过 mergeOrderedMessages 统一排序和去重，新增 message-order.ts 及其独立 Node 测试覆盖高 ID 先到、重复事件和历史游标边界。
变更文件：apps/screen-web/src/App.vue；apps/screen-web/src/components/realtime/DanmakuOverlay.vue；apps/screen-web/src/components/realtime/message-order.ts；apps/screen-web/scripts/test-message-order.mjs；apps/screen-web/package.json；apps/screen-web/AGENTS.md；README.md；WIKI.md；MEMORY.md；工作流资料。
风险或阻塞：尚未对本轮新增的普通入口恢复和乱序补齐逻辑执行完整回归、Windows 安装包构建与独立审核；旧测试证据不覆盖本轮变更。
下一步：以 WORKPACKAGE-v5.json 冻结的 46 个实施文件作为输入，由测试角色执行后端、渲染器单测、全量构建、Electron 类型检查和 NSIS 安装包构建。

实现摘要：

- 大屏仅在 URL 查询参数包含 danmaku-overlay 时加载弹幕渲染器，普通入口恢复活动数据大屏基础页面。
- 弹幕 WebSocket 的 message.created 不再直接改变游标；渲染器保存事件 ID 后调用消息游标接口，按 ID 升序合并、去重和投放。
- 连接恢复仍以 lastMessageId 为游标；HTTP 暂时失败时保留待处理事件，避免临时网络故障导致跳过消息。
- 该补充不改变 TASK-v1 的接口、配置字段、token 规则或 Electron 权限边界。
