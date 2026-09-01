任务：
TASK-v1：优化抽奖大屏方屏、横屏与竖屏布局

输入版本：
TASK-v1；输入 HEAD `807bd2238db9b07e4fb860b1476960bd06216008`，工作树初始干净

状态：completed

结论：
已按冻结任务实现响应式布局。普通页面以 1:1 宽高比为分界，方屏和横屏继续左右并列；严格小于 1:1 的竖屏改为主抽奖区在上、奖项进度板在下的两行网格。竖屏奖项板限制高度并保留板内滚动，小方屏额外收紧两列宽度和文案尺寸。

证据：
- `apps/screen-web/src/components/lottery/LotteryScreen.css:117` 使用弹性右列，基础布局保持左右结构。
- `apps/screen-web/src/components/lottery/LotteryScreen.css:340-397` 通过 `max-aspect-ratio: 1 / 1` 与方屏覆盖规则精确区分严格小于 1:1 的竖屏和 1:1 方屏，并将竖屏奖项板放回普通文档流。
- `apps/screen-web/src/components/lottery/LotteryScreen.css:373-400` 对方屏/小横屏收紧右列、内边距和文字尺寸，避免窄视口内容拥挤。
- `apps/screen-web/src/components/lottery/LotteryScreen.css:402-435` 保留移动端紧凑规则，并单独优化小方屏可读性。
- AC-001/AC-002 已通过 1280×720、844×390、1024×768、768×768、390×390、1000×1001、390×844、1080×1920 浏览器视口检查；所有检查视口的文档滚动宽高均等于视口。

变更文件：
- `apps/screen-web/src/components/lottery/LotteryScreen.css`
- `apps/screen-web/AGENTS.md`
- `apps/screen-web/src/components/lottery/AGENTS.md`
- `MEMORY.md`、`LEARNING.md`、`WIKI.md`

风险或阻塞：
未发现阻塞。极窄方屏仍按用户要求保持左右布局，可视空间有限时依赖紧凑字号；当前未接入真实活动快照的长奖项数据做内容量压力测试。

下一步：
执行 screen-web 类型检查、既有抽奖脚本测试、生产构建和最终代码审核/场景验收。
