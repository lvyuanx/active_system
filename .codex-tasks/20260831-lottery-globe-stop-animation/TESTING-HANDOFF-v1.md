任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1；开发输入：DEVELOPMENT-HANDOFF-v1
状态：completed
结论：阻断测试通过，阶段转换、公开事件顺序、高人数渲染和构建验证通过。
证据：`python -m pytest -q apps/backend/tests`：57 passed、7 个既有弃用警告；`python -m pytest -q apps/backend/tests/test_lottery_round.py`：2 passed；`pnpm --filter @active/screen-web test`：所有脚本通过；screen-web/admin-web typecheck 通过；screen-web/admin-web build 通过；`git diff --check` 通过。
变更文件：新增 `lottery.draw.stopping` 事件断言、球体散开/聚焦数学测试和对应模块文档。
风险或阻塞：未使用真实 1920×1080 浏览器视口，本环境 in-app Browser 实际报告 1280×720；已在 1280×720 隔离数据场景覆盖 300 人。
下一步：由审核角色检查接口兼容、性能与异常路径，再由验收角色按 AC 逐项确认。

## 用例映射

- AC-001：源码检索确认 `globe-focus` 不存在，`LotteryGlobe.css` 无中心十字规则。
- AC-002/AC-005/AC-006：`test_lottery_round.py` 验证 stopping 先于 result/drawn、重复停止幂等；`active_round` 和 phase 类型检查通过。
- AC-003/AC-004/AC-007：隔离浏览器场景观察 300 人 scattered/selecting/revealed 画面，页面无溢出。
- AC-008：后端全量测试、前端单元脚本、类型检查、生产构建和 diff check 通过。
