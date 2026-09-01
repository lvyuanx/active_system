任务：调整大屏活动名与奖品信息布局
输入版本：TASK-v5
状态：completed
结论：已将活动名称移至顶部 Header；顶部标题区显示当前奖品名称和可选图片；主抽奖面板移除重复奖品名称与中奖奖品图片。
证据：

- `LotteryScreen.vue` 使用 Header 的 `header-activity-name` 展示快照活动名称。
- `title-prize` 使用进行中轮次、最近开奖结果或下一件有库存奖品确定名称和图片；图片失败时仍保留名称。
- `LotteryScreen.css` 和 `LotteryScreenImages.css` 提供 Header 居中、奖品图文横排及移动端尺寸规则。
- 球体、中奖者放大层、开奖事件处理和奖品板逻辑未改动；回归断言覆盖新布局及旧主面板奖品元素移除。

变更文件：

- `apps/screen-web/src/components/lottery/LotteryScreen.vue`
- `apps/screen-web/src/components/lottery/LotteryScreen.css`
- `apps/screen-web/src/components/lottery/LotteryScreenImages.css`
- `apps/screen-web/scripts/test-lottery-globe.mjs`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`
- `LEARNING.md`
- `WIKI.md`
- `.codex-tasks/20260831-lottery-center-reveal/`

风险或阻塞：无；保留工作区中用户已有的其它代码和媒体变更。
下一步：进入测试、审核和场景验收。
