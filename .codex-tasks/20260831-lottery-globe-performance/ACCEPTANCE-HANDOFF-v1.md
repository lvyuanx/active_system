任务：验收高人数抽奖球体性能与可读性优化
输入版本：TASK-v1；审核输入：REVIEW-HANDOFF-v1
状态：completed
结论：ACCEPTED。
证据：300 人隔离场景中 rolling 阶段显示全部用户头像/光点和有限前景姓名，姓名不再形成截图中的文字团块；stopping 后约 2.2 秒进入 revealed，中奖用户卡片显示且居中；页面无滚动，自动化检查全部通过。
变更文件：验收阶段未修改生产文件；已同步 screen-web 模块文档、`MEMORY.md`、`LEARNING.md`、`WIKI.md` 和任务证据。
风险或阻塞：无未解决验收阻塞；极端超大规模和真实硬件 FPS 监控保留为后续性能专项。
下一步：清理临时运行服务和隔离数据，保留源码与交接证据。

逐项结果：

- AC-001 PASS：300 位参与者全部生成球面点；高密度档位只限制头像/姓名细节，姓名通过深度和屏幕空间矩形避让。
- AC-002 PASS：每帧使用一次旋转矩阵，旋转点和投影条目复用；头像圆形 Canvas 与球体引导线缓存。
- AC-003 PASS：超过 260 人 profile 为 `frameStride=2`、`pixelRatioCap=1.25`，测试断言通过。
- AC-004 PASS：浏览器停止后进入 stopping，约 2.2 秒后中奖卡片显示，中奖者为高密度用户并位于中心。
- AC-005 PASS：数学测试覆盖空/普通/高密度 profile；本地布局缺失时仍保留事件用户名和默认头像回退逻辑。
- AC-006 PASS：未修改后端协议和开奖逻辑；既有 screen-web 类型、构建和全仓回归通过；页面 document/body 无溢出。
- AC-007 PASS：screen-web 测试、typecheck/build、全仓 typecheck/build、compileall、diff check 和浏览器实测均通过。
