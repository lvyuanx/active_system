# ARCHITECTURE-v2：多测试用户并发弹幕发送

## 方案

`DanmakuTestManager._run` 为每个 `TestUser` 创建一个 asyncio sender task。第 `i` 个用户从 `TEST_MESSAGES[i % len(TEST_MESSAGES)]` 开始，之后每轮步进 `user_count`，从而保持用户独立且避免所有用户发送相同正文。

首条消息延迟为 `min(max_delay_seconds, 1.0) * index / user_count`；首轮错峰完成后，每个 sender 独立调用 `random.uniform(min_delay_seconds, max_delay_seconds)` 等待。

## 并发与一致性

- `_run` 创建活动级 `asyncio.Lock`，sender 在锁内完成 `create_message`、聊天室广播和弹幕广播，避免 SQLite 写入竞争和消息广播顺序混乱。
- `_run` 使用 `asyncio.wait(..., return_when=FIRST_COMPLETED)` 监控 sender；任一 sender 因活动只读、发送异常或取消而结束时，取消并回收该活动所有 sender。
- `stop(activity_id)` 继续取消活动根任务；根任务 finally 必须取消并 await 全部 sender，不能遗留后台协程。

## 接口与兼容

`DanmakuTestConfig`、管理端请求/回包、聊天室消息和弹幕消息格式不变。`user_count` 仍至少为 1 且不设置应用层上限；渲染端的轨道容量和队列丢弃规则不变。

## 测试重点

- 用 3 个以上测试用户验证每个用户均独立发送、首轮错峰和独立延迟。
- 验证停止/只读状态会回收全部 sender，且真实聊天室和弹幕广播仍收到同一条消息。
- 保留配置范围、默认值、活动隔离、类型检查、构建和 NSIS 打包回归。
