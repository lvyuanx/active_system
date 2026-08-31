任务：抽奖球体停止、打散与中奖聚焦
输入版本：TASK-v1；审核输入：REVIEW-HANDOFF-v1
状态：completed
结论：ACCEPTED
证据：后端 57 条测试、两条轮次专项测试、screen-web 测试/typecheck/build、admin-web typecheck/build 均通过；隔离浏览器 300 人场景观察 stopping 后 scattered、selecting、revealed；1280×720 下 document/body/viewport 无溢出，控制台 warn/error 为空。
变更文件：验收未修改生产文件；补充本交接、项目知识和模块说明。
风险或阻塞：未在真实 1920×1080 硬件上执行专项浏览器测试；本地 in-app Browser 的实际视口为 1280×720。其余 AC 无阻塞。
下一步：清理本轮临时服务和隔离测试进程，保留源码与证据。

逐项结果：

- AC-001 PASS：移除 `globe-focus` DOM/CSS，源码检索无匹配；中奖阶段使用光环和卡片，不绘制中心十字。
- AC-002 PASS：后端专项测试收到 `lottery.draw.stopping` 后才收到 result/drawn；rotation 仅在 rolling 更新。
- AC-003 PASS：隔离浏览器在 stopping 事务暂缓期间显示散开后的用户点和 `等待中奖者聚焦`，没有继续成球滚动。
- AC-004 PASS：selecting 画面显示中奖用户居中、放大和光环；revealed 画面显示单一中心中奖卡片。
- AC-005 PASS：重复停止返回已有结果且不重复广播 drawn；原有后端全量回归通过。
- AC-006 PASS：ready 使用 `active_round.phase` 恢复停止阶段；多连接 stopping 事件专项断言通过。
- AC-007 PASS：300 人 1280×720 浏览器画面用户点位分散、姓名受限，无横向/纵向溢出，控制台无 warn/error。
- AC-008 PASS：后端 pytest、screen-web 脚本/typecheck/build、admin-web typecheck/build、diff check 通过。
