任务：TASK-v5 活动聊天室输入框默认高度校准
输入版本：TASK-v5
状态：completed
结论：完成输入框高度修复。移除 Vant Field 的可见字数提示属性，保留 `maxlength=500`；输入 Field 使用零垂直内边距、内容垂直居中、`min-height:44px`，textarea 保留 24px 行高和 72px 最大可视高度。默认空输入和一行输入时 Field 与发送按钮实际均为 44px；两行、三行及超三行输入保持可编辑。
证据：

- `apps/user-web/src/views/activity/chat.vue:29-38` 保留 `maxlength="500"`、`rows="1"` 和 `autosize` 的 `minHeight:24`、`maxHeight:72`，不再渲染字数提示。
- `apps/user-web/src/views/activity/chat.css:131-157` 设置 Field `align-items:center`、`padding:0 10px`、`min-height:44px`；textarea 设置 `min-height:24px`、`max-height:72px`、`line-height:24px`。
- 390×450 和 430×932 浏览器尺寸、三行上限、超三行内部滚动、导航/Tabbar/横向溢出证据见 `BROWSER-EVIDENCE-v5.md`。
- `pnpm --filter @active/user-web typecheck` 退出码 0。
- `pnpm --filter @active/user-web build` 退出码 0，Vite 转换 335 个模块。
- 目标文件 `git diff --check` 退出码 0。

变更文件：

- `apps/user-web/src/views/activity/chat.vue`
- `apps/user-web/src/views/activity/chat.css`
- `apps/user-web/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260826-activity-chat-ui/TASK-v5.md`

风险或阻塞：主工作树包含前序头像和聊天改造的未提交用户改动，未创建隔离 worktree；本版本未修改这些资源或聊天协议。390px 截图接口超时，但 DOM 尺寸、交互状态和 430px 视觉截图均已取得。
下一步：执行独立测试交接、审核和产品验收。

