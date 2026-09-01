任务：抽奖进行中标签展示奖品图片
输入版本：TASK-v3
状态：completed
结论：已在大屏进行中轮次的顶部奖品标签中按当前轮次奖项/奖品 ID 匹配公开快照图片；图片存在时显示缩略图，文字始终保留，加载失败时隐藏图片并保留文字。
证据：

- `apps/screen-web/src/components/lottery/LotteryScreen.vue` 的 `activePrizeImageURL` 从 `snapshot.awards` 匹配当前 `activeRound` 的 `award_id`、`prize_id`。
- 标签使用 `.round-prize-chip__image`，复用 `imageURL`、`canShowImage` 和 `markImageFailed` 的安全图片解析与失败回退。
- `LotteryScreen.css` 与 `LotteryScreenImages.css` 增加紧凑的图片/文字横向布局及移动端尺寸。
- 回归断言覆盖图片元素、URL 解析、失败回退和图片样式选择器。

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

风险或阻塞：当前浏览器活动没有进行中轮次，未通过真实开奖操作捕获标签动画帧；为避免改变用户活动数据，保留该视觉覆盖缺口。现有奖品图片在奖品板中已实际加载。
下一步：进入测试、审核和场景验收。
