# 浏览器运行证据

测试环境：隔离 SQLite/媒体目录、FastAPI `127.0.0.1:8004`、管理端 `127.0.0.1:5189`、大屏 `127.0.0.1:5190`，活动包含 24 位测试用户。

- 初始 ready：管理端显示“已连接”和“开始抽奖”；大屏公开连接正常。
- 点击“开始抽奖”约 700ms 后：管理端显示“停止抽奖”；大屏 `data-lottery-phase=rolling`、`data-participant-count=24`，DOM 文本为“所有参与者正在滚动”。
- 开始后重载大屏：ready 携带 `active_round`，重载后仍为 `rolling` 且人数为 24；管理端仍显示“停止抽奖”。
- 1280×720 测量：`document.documentElement.scrollWidth=1280`、`scrollHeight=720`，`window.innerWidth=1280`、`innerHeight=720`；rolling 与 revealed 阶段均相同。
- 点击“停止抽奖”约 120ms 后：大屏进入 `stopping`，无中奖卡片。
- 再等待约 2400ms：大屏进入 `revealed`，DOM 显示“中奖者”和具体用户名；截图显示球体与中奖卡片，中奖用户位于中心。
- 开奖完成后重载大屏：ready 恢复最新中奖用户名和历史库存，但不再次播放减速揭晓动画。
- 管理端复测：结果到达后按钮恢复“开始抽奖”，历史记录和奖品剩余库存同步更新。
- 控制台：最终 reload 后的流程未再产生新的运行时异常；此前热更新残留错误未在最终 reload 后重现，管理端连接状态由 ready 首帧确认。
