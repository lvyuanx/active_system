# 浏览器运行证据

测试环境：隔离 SQLite 数据库、FastAPI `127.0.0.1:8005`、管理端 `127.0.0.1:5191`、大屏 `127.0.0.1:5192`；活动内准备 300 位参与者，奖品库存足够，使用 screen-web 公开大屏连接触发真实轮次事件。

- rolling 阶段：`data-lottery-phase=rolling`、`data-participant-count=300`；画面保留全部参与者的球面运动，前景姓名数量受限，其他用户显示头像或低成本光点。
- 1280×720 测量：`document.documentElement.scrollWidth=1280`、`scrollHeight=720`，`window.innerWidth=1280`、`innerHeight=720`。
- stop 阶段：页面进入 `stopping`，中奖卡片未提前出现。
- 约 2.4 秒后：页面进入 `revealed`，`data-winner-card` 显示高密度用户中奖姓名，球体停止在目标角度。
- 控制台：本次高人数 rolling/revealed 流程未出现新的运行时错误或头像加载阻断。
