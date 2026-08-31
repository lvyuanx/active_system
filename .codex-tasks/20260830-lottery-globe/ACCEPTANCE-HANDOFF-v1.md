任务：验收抽奖球体动画与开始/停止开奖
输入版本：TASK-v1；审核输入：REVIEW-HANDOFF-v1
状态：completed
结论：ACCEPTED。
证据：后端 round 测试、screen-web 球体测试、两端 typecheck/build 和浏览器实际流程均通过；浏览器 1280×720 DOM 检查得到 `documentElement/body` 宽高均为 1280×720，rolling/stopping/revealed 阶段均无溢出；滚动截图显示全部 24 位开始时冻结用户，揭晓截图显示中奖用户卡片居中。
变更文件：验收阶段未修改生产文件；补充了本交接证据和项目进度/经验记录。
风险或阻塞：无未解决验收阻塞；多副本共享消息总线和目标硬件专项测试仍属于后续部署工作。
下一步：执行临时服务/隔离数据库清理，保留源码和任务证据。

逐项结果：

- AC-001 PASS：浏览器实际检查 1280×720 下 document、body 和页面根节点无横向/纵向溢出，CSS 使用 `100dvh`、`min-height: 0`、`overflow: hidden`。
- AC-002 PASS：后端开始测试确认中奖记录数为 0；公开开始 participants 包含活动全部用户且仅含三项安全字段。
- AC-003 PASS：浏览器开始后管理端按钮变为“停止抽奖”，大屏 `data-lottery-phase=rolling` 且球体持续刷新。
- AC-004 PASS：停止阶段先进入 `stopping`，后端提交后收到结果；测试确认中奖记录写入并广播结果。
- AC-005 PASS：后端测试确认开始后注册用户不在中奖候选；停止前对黑名单/停用状态复核，中奖者来自开始时冻结合资格集合。
- AC-006 PASS：轮次期间配置 PUT、名单 PUT 和 reset 返回 409；管理端奖品、图片、名单控件置灰。
- AC-007 PASS：重复 stop 返回 `idempotent=true`，数据库仍只有一条记录且不重复发送大屏 drawn。
- AC-008 PASS：ready 恢复 active_round；多个管理端同步 started/result，大屏按 draw_id 去重；大屏 ready 历史恢复最新中奖者。
- AC-009 PASS：公开开始/中奖事件字段断言不含手机号、名单标记、停用状态和管理员字段；旧 draw.request 回归通过。
- AC-010 PASS：球体数学测试验证 120 个单位 Fibonacci 点、透视目标和 ease-out；浏览器 2.2 秒后中奖者卡片居中，缺失本地点时有默认头像回退。
- AC-011 PASS：后端 57 条、screen-web 测试、compileall、两端类型检查/构建、全仓 typecheck 和 diff check 均通过，模块文档和项目知识已同步。
