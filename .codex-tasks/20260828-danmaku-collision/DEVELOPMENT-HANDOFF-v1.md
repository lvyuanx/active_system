任务：按 TASK-v1 实现 B站式弹幕碰撞避让、最大等待时间配置及兼容迁移。
输入版本：TASK-v1；架构输入为 ARCHITECTURE-v1；输入快照为 HEAD-9ec1caa4-dirty-20260828。
状态：completed
结论：已完成后端配置与旧 SQLite 增量迁移、管理端配置控件、screen-web 碰撞几何与 FIFO 等待队列、Electron 会话类型同步，并保留 CSS 位移动画和统一帧生命周期调度。
证据：
- `apps/backend/app/core/database.py:53,102-107` 增加 `max_wait_seconds` 默认值、范围约束和旧表检测迁移。
- `apps/backend/app/modules/danmaku/service.py:20,34,124-195` 完成默认值、Pydantic 范围校验、写入、读取和更新 SQL；旧客户端省略字段时仍使用 1.5 秒默认值。
- `apps/screen-web/src/components/realtime/danmaku-layout.ts:82-158` 按实测宽度、运动轨迹、生命周期交集、入/出屏边界和 8px 间距判断碰撞，并从轮询游标查找安全轨道。
- `apps/screen-web/src/components/realtime/DanmakuOverlay.vue:164-211,379-395` 在本地入队时计时，按最大等待时间 FIFO 丢弃，使用与几何模型一致的 CSS transform 动画入场，不再逐帧写入元素位移。
- `apps/admin-web/src/views/danmaku/index.vue:93,202` 和三端 API/session 类型已同步新字段；受影响模块 AGENTS、MEMORY、LEARNING、WIKI 已同步。
- 实现过程中未创建提交，保留输入工作树中的既有未提交弹幕改动。
变更文件：后端数据库/弹幕服务/测试，管理端弹幕设置与类型，screen-web 碰撞模块/渲染器/测试，Electron 类型，模块文档和项目知识文件；完整清单以工作树快照为准。
风险或阻塞：Canvas 字体测量受字体回退影响，算法保留 8px 安全间距并采取保守判断；活动弹幕的实际运动由 CSS 负责，浏览器入口检查不能替代 Electron 原生桥接注入验证。
下一步：交由测试、审核和验收阶段依据 TASK-v1 逐条验证。
