# 浏览器验收证据

任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1；测试输入：TESTING-HANDOFF-v1
状态：completed
结论：隔离数据场景下停止交互视觉链路通过。
证据：使用临时 SQLite 数据库和 300 位活动用户，服务运行在本机临时端口 8005/5191/5192；in-app Browser 实际视口为 1280×720。管理端 WebSocket 触发 start/stop，终端依次收到 `lottery.draw.started`、`lottery.draw.stopping`、`lottery.draw.result`。停止后浏览器画面观察到用户点向外散开并显示“等待中奖者聚焦”，结果到达后观察到“WINNER FOCUS”、中奖用户位于中心并带青色光环，随后显示“WINNER REVEALED”中心卡片。`documentElement.scrollWidth/scrollHeight` 为 1280/720，`window.innerWidth/innerHeight` 为 1280/720；`tab.dev.logs({levels:["error","warn"]})` 返回空数组。
变更文件：浏览器未修改源码；使用的数据库、媒体和服务均在 `C:/Users/Administrator/AppData/Local/Temp/` 临时目录。
风险或阻塞：in-app Browser 不接受本轮期望的 1366/1920 视口覆盖，未宣称这些尺寸已实测；仍保留 100dvh/overflow hidden 的代码级约束。
下一步：停止本轮服务、关闭临时浏览器标签并完成最终工作树检查。
