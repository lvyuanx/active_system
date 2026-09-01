任务：实时抽奖特殊配置安全码
输入版本：TASK-v1；开发交接：DEVELOPMENT-HANDOFF-v1.md
状态：completed
结论：阻断测试通过，未发现本次改动导致的后端抽奖回归或管理端类型/构建问题。
证据：`python -m pytest -q`（`apps/backend`）结果为 58 passed、退出码 0；其中安全码用例覆盖未配置 503、未认证 401、错误码 403、正确码 200、活动不存在 404 且错误响应不包含正确码；`pnpm --filter @active/admin-web typecheck` 和 `pnpm --filter @active/admin-web build` 均退出码 0；`git diff --check` 退出码 0；构建产物敏感字段扫描为空。
变更文件：仅补充 `apps/backend/tests/test_lottery.py` 测试资产，未修改生产代码；测试副作用产生的后端临时媒体已移出并恢复基线图片。
风险或阻塞：无自动化浏览器交互测试，前端入口行为通过 typecheck、构建产物扫描和源码控制流检查验证；Element Plus 弹窗的最终视觉效果仍可在部署环境手工确认。
下一步：按测试证据进入只读审核，再执行逐条验收和清理门禁。
