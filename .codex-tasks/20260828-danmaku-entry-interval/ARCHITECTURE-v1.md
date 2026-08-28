# ARCHITECTURE-v1：弹幕完整进入后间隔入场

## 方案

在现有运动矩形碰撞预测前增加同轨道 ready gate。对从 `left = viewportWidth` 移动到 `left = -textWidth` 的弹幕，完整进入时间为：

```text
fullyEnteredAt = startedAt + durationMs * textWidth / (viewportWidth + textWidth)
nextEntryAt = fullyEnteredAt + entryIntervalMs
```

候选弹幕只有在同轨道所有活动弹幕的 `nextEntryAt <= now` 后，才进入现有全生命周期碰撞预测；不同轨道不检查该时间门槛。轨道从轮询游标开始搜索，安全轨道优先入场。

## 数据与接口

- 新增 `entry_interval_seconds: float` 到后端/管理端/screen-web/Electron 设置类型。
- SQLite 字段为 `REAL NOT NULL DEFAULT 1.0 CHECK(entry_interval_seconds BETWEEN 0.1 AND 5.0)`。
- `init_database` 用 `PRAGMA table_info` 检测后增量加列；更新模型默认 1.0，兼容旧请求体。
- 现有 HTTP 与 WebSocket 设置载荷自动带字段，不新增消息类型。

## 运行时与配置更新

- 活动项保存 `track`、`width`、`startedAt`、`durationMs`，几何模块计算完整进入和 ready 时间。
- 当前活动项继续沿用原 CSS 样式和飞行参数；最新入场间隔只影响未来入场判断。
- 所有轨道不可用时保留本地入队时间、50ms 重试、200 条 FIFO 上限和既有最大等待丢弃策略。

## 测试重点

- 几何：完整进入前阻止、达到间隔后允许、单轨道仍在屏内、不同轨道立即可用、长弹幕追赶和轮询。
- 后端：默认值、迁移、边界、非法值、旧请求体、HTTP/WS 字段。
- 回归：消息排序、统一调度器、重连补齐、设置更新、多屏、类型检查、构建和 NSIS 打包。
