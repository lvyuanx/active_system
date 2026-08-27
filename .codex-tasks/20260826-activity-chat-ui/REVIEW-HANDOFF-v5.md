任务：TASK-v5 活动聊天室输入框默认高度校准
输入版本：TASK-v5
状态：completed
结论：APPROVED（主 Agent 按首次审核意见完成只读复核；独立复审线程未返回可用正文）
证据：

- `apps/user-web/src/views/activity/chat.vue:29-38` 保留 `maxlength="500"`、`rows="1"` 和 24/72px autosize，未修改消息协议、发送条件或连接逻辑。
- `apps/user-web/src/views/activity/chat.css:131-157` 将 Field 最小高度设为 44px、上下内边距设为 0、内容垂直居中；发送按钮固定为 44px。
- 390×450 空输入和一行输入 Field/按钮均为 44px，底边差为 0px；两行 textarea/Field/按钮为 48/50/44px；三行 textarea/Field/按钮为 72/74/44px；超三行 clientHeight=72px、scrollHeight=96px。
- `WORKPACKAGE-v5.json` 的实际文件清单覆盖代码、模块/项目文档、v5 任务单、补丁、任务图、开发/测试/集成/浏览器证据和截图，哈希校验脚本返回 `MANIFEST_SHA256_OK`。
- v5 限定补丁在预览 worktree 中前置检查、实际应用和反向检查均退出码 0，命令均明确使用 `--ignore-whitespace` 处理 Windows 行尾。
- `pnpm --filter @active/user-web typecheck`、`pnpm --filter @active/user-web build` 和目标文件 `git diff --check` 均退出码 0。

变更文件：无
风险或阻塞：390×450 截图接口连续超时，短屏 DOM/像素状态已验证；主工作树含前序用户未提交改动，未创建隔离开发 worktree。独立复审线程因平台未返回正文，结论由主 Agent 依照首次审核整改项复核，不把平台未响应当作代码通过证据。
下一步：按 TASK-v5 AC-001 至 AC-011 逐条验收。

