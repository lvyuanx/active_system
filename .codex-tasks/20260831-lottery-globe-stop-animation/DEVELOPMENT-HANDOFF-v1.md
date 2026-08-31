任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1；架构输入：ARCHITECTURE-v1
状态：completed
结论：已完成停止即时冻结、球体打散、中奖聚焦和中心十字移除，并保持开奖事务与脱敏边界。
证据：后端 `LotteryRoundPublic.phase` 支持 `rolling/stopping`；`protocol.py` 在 `draw_lottery` 前广播 `lottery.draw.stopping`；`LotteryGlobe.vue` 使用 `scattering -> scattered -> selecting -> revealed`，rotation 只在 rolling 阶段更新；screen-web 单元脚本和后端轮次测试通过。
变更文件：`apps/backend/app/modules/lottery/models.py`、`round_state.py`、`protocol.py`、`apps/backend/tests/test_lottery_round.py`；`apps/screen-web/src/components/lottery/LotteryGlobe.vue`、`LotteryGlobe.css`、`LotteryScreen.vue`、`lottery-globe-math.ts`、`lottery-globe-assets.ts`、`lottery-globe-canvas.ts`、`AGENTS.md`；`apps/admin-web/src/api/client.ts`、`useLotteryRoundControl.ts`；项目文档和本任务证据。
风险或阻塞：工作树包含此前 lottery 任务的未提交变更，按 `DIRTY_INPUT_UNSAFE` 使用主工作树单写入者串行完成；未创建 Git 提交。
下一步：执行完整后端/前端回归、浏览器停止流程和最终审核验收。
