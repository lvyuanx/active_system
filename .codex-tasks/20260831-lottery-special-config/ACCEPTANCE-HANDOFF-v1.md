任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；审核交接：REVIEW-HANDOFF-v1.md
状态：completed
结论：ACCEPTED
证据：AC-001 PASS：正确安全码由后端接口验证后才执行 `entryDialogVisible.value = true`；AC-002 PASS：密码式输入、空值前端校验、错误码不会打开弹窗且错误响应不回传正确码；AC-003 PASS：后端用例证明未配置/未认证/活动不存在均被拒绝；AC-004 PASS：后端 58 passed、管理端 typecheck/build、`git diff --check` 和构建产物敏感字段扫描通过。
变更文件：验收覆盖 `.env.example`、README、管理端 lottery API/页面/文档、后端 Settings/lottery 模块/测试和项目知识/任务证据文件。
风险或阻塞：无阻断项；上线前仍需在部署环境 `.env` 设置实际安全码并重启后端。
下一步：完成临时测试产物核对、写入最终 TaskGraph 状态并向用户交付。
