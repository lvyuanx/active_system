# 抽奖模块说明

## 模块简介

`lottery` 提供按 `activity_id` 隔离、并按 `prize_id` 细分名单规则的奖项、奖品、中奖记录和实时 WebSocket 协议，
是管理端与大屏端之间的唯一抽奖消息中枢。

## 目录说明

- `models.py`：配置、奖品图片、历史、中奖事件、抽奖轮次和错误的 Pydantic/dataclass 协议模型。
- `repository.py`：SQLite 行读取、配置摘要、奖品级名单分页查询、名单状态转换和管理员/公开中奖对象转换，并负责旧名单数据迁移。
- `service.py`：配置/历史查询、名单即时更新、开始时候选池准备、候选资格计算、事务开奖和幂等。
- `round_state.py`：活动级单进程抽奖轮次、开始名单、内部候选用户快照和 stopping 阶段。
- `protocol.py`：管理员 WebSocket 的开始、停止、旧协议兼容、重置和错误事件处理。
- `state.py`：抽奖操作共享异步锁。
- `snapshot.py`：公开/管理员 ready 与 reset 快照及安全字段裁剪。
- `router.py`：管理员配置/历史 HTTP 接口、管理员 JWT 首帧认证 WS、公开只读大屏 WS 和事件分发。
- `media_service.py`：奖品图片上传、替换、移除、管理员/公开读取和孤儿文件扫描。
- `manager.py`：进程内活动房间连接管理，按 `admin`/`screen` 角色广播并清理失败连接。

## 数据流

管理员通过 HTTP 读取奖项、奖品、规则和指定奖品的名单摘要；特殊配置入口先调用
`POST /admin/activities/{activity_id}/lottery/security-code/verify` 校验后端配置的安全码，再打开名单弹窗。
名单通过 `/admin/activities/{activity_id}/lottery/entries?prize_id={prize_id}` 按指定奖品的关键词、状态和页码查询，并通过其单用户
`PUT` 接口即时保存该奖品的黑白名单。`lottery_prize_entries` 是当前名单表，旧的 `lottery_entries` 仅作为历史活动级名单的迁移来源；
每个活动只执行一次迁移，已存在的奖品复制旧标记，迁移后的新奖品默认没有黑白名单标记。配置保存不会再全量替换名单。管理员通过 WS 先发送 `lottery.draw.start`，后端冻结开始时的全部公开用户和合资格用户 ID，
再广播 `lottery.draw.started`；停止时先将轮次标记为 stopping 并广播不含中奖信息的 `lottery.draw.stopping`，再处理
`lottery.draw.stop`。管理员切换抽取奖品时发送 `lottery.prize.select`，服务端校验启用状态和库存后维护活动级当前奖品，
并广播公开的 `lottery.prize.selected`；两个 WS 首次连接的 `lottery.ready` 也带当前选中奖品 ID。开奖服务在 `BEGIN IMMEDIATE` 事务中重新校验奖品、库存、
停用状态、跨奖品去重和冻结候选池，写入成功并提交后，router 才向管理员发送完整结果、向大屏发送带轮次 ID的无手机号
`lottery.drawn`。相同轮次停止使用 `(activity_id, round_id)` 幂等；旧客户端仍可使用 `lottery.draw.request`。
配置保存通过 HTTP 成功后广播安全的 `lottery.config.updated`。

奖品图片通过独立 multipart 接口处理，不进入配置 PUT JSON；图片使用随机 key 保存，并以
`/api/v1/activities/{activity_id}/lottery/prizes/{prize_id}/image?v={image_id}` 作为公开安全引用。
替换和移除在数据库提交后清理旧文件，启动和配置操作后扫描无引用文件作为崩溃补偿。
图片上传和移除与配置/开奖共用 lottery operation lock，提交后读取最新配置并广播安全的
`lottery.config.updated`，确保公开大屏实时收到图片绑定变化。
公开图片读取要求携带当前 `image_id` 版本参数，管理员读取仍可选版本且不缓存；媒体根目录由 `MEDIA_ROOT` 配置。
配置事务开始快照活动全部媒体引用，提交前计算剩余引用差集，因此奖项级联删除也能及时回收图片；
事务因中奖记录失败时不会触发清理。

## 安全与并发

- 管理员 WS 必须使用超级用户 JWT，拒绝活动用户上下文和非管理员凭证；大屏 WS 不要求凭证但只能读取。
- 特殊配置安全码只从后端 `LOTTERY_SECURITY_CODE` 读取，校验接口要求超级用户 JWT、校验活动存在性并使用常量时间比较；安全码不进入响应或公开快照。
- 公开快照、开奖事件和重置事件不包含手机号、黑名单、白名单、停用状态或管理员字段。
- `(activity_id, request_id)` 唯一保证请求重试幂等；重试只返回已有结果，不重复广播大屏。
- 每个活动同时只能存在一个内存抽奖轮次；轮次期间禁止修改抽奖配置和黑白名单，服务重启会取消未落库轮次。
- 公开开始事件只返回活动用户 ID、用户名和头像 ID，不返回候选资格、手机号、停用状态或名单标记。
- `lottery.draw.stopping` 只返回 `round_id`/`request_id`，用于大屏立即冻结旋转；中奖信息仍只能在事务提交后的结果事件中出现。
- 剩余库存由奖品数量减中奖记录实时计算，避免单独库存字段与记录分叉。
- 名单查询使用 `LEFT JOIN` 对缺失的奖品名单行按可参加处理，并复用当前奖品的开奖资格条件；名单更新先校验活动用户和奖品归属，再以
  `BEGIN IMMEDIATE` upsert `(activity_id, prize_id, activity_user_id)` 单行状态。
- 连接管理器是单进程实现，多副本部署需后续接入共享消息总线。
