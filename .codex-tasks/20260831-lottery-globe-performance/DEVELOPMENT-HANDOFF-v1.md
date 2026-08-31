任务：实现高人数抽奖球体性能与可读性优化
输入版本：TASK-v1；架构输入：ARCHITECTURE-v1
状态：completed
结论：完成 Canvas 球体高人数分层渲染、姓名屏幕空间避让、旋转矩阵与投影对象复用、头像/引导线缓存、隔帧绘制和自适应像素比；后端和 WebSocket 协议未修改。
证据：`apps/screen-web/src/components/lottery/LotteryGlobe.vue` 保留全部用户点位并将非细节用户绘制为光点；`lottery-globe-math.ts` 提供四档渲染 profile、矩阵和原地旋转；300 人浏览器截图显示画面不再文字成团。
变更文件：`apps/screen-web/src/components/lottery/LotteryGlobe.vue`、`lottery-globe-math.ts`、`scripts/test-lottery-globe.mjs`、screen-web lottery 模块文档、`MEMORY.md`、`LEARNING.md`、`WIKI.md` 和本任务证据。
风险或阻塞：极端超大名单仍包含 CPU 深度排序成本；多千用户场景可进一步使用 WebGL 或分批布局。当前无阻塞。
下一步：交由测试执行 screen-web 测试、类型检查、构建和高人数浏览器验收。
