# 抽奖模块说明

## 模块简介

`lottery` 提供按 `activity_id` 隔离的奖项、奖品、抽奖名单、中奖记录和实时 WebSocket 协议，是管理端与大屏端之间的
唯一抽奖消息中枢。

## 目录说明

- `models.py`：配置、奖品图片、历史、中奖事件和错误的 Pydantic/dataclass 协议模型。
- `repository.py`：SQLite 行读取、配置摘要、名单分页查询、名单状态转换和管理员/公开中奖对象转换。
- `service.py`：配置/历史查询、名单即时更新、候选资格计算、事务开奖和幂等。
- `snapshot.py`：公开/管理员 ready 与 reset 快照及安全字段裁剪。
- `router.py`：管理员配置/历史 HTTP 接口、管理员 JWT 首帧认证 WS、公开只读大屏 WS 和事件分发。
- `media_service.py`：奖品图片上传、替换、移除、管理员/公开读取和孤儿文件扫描。
- `manager.py`：进程内活动房间连接管理，按 `admin`/`screen` 角色广播并清理失败连接。

## 数据流

管理员通过 HTTP 读取奖项、奖品、规则和名单摘要；名单通过
`/admin/activities/{activity_id}/lottery/entries` 按关键词、状态和页码查询，并通过其单用户 `PUT` 接口即时保存黑白名单。
配置保存不会再全量替换名单。管理员通过 WS 发送 `lottery.draw.request` 或 `lottery.reset.request`。开奖服务在同一
`BEGIN IMMEDIATE` 事务中校验活动状态、库存、黑白名单、停用用户和跨奖品去重，写入成功并提交后，router 才向管理员
发送完整结果、向大屏发送无手机号的 `lottery.drawn`。配置保存通过 HTTP 成功后广播安全的
`lottery.config.updated`；两个 WS 首次连接都收到按权限生成的 `lottery.ready`。

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
- 公开快照、开奖事件和重置事件不包含手机号、黑名单、白名单、停用状态或管理员字段。
- `(activity_id, request_id)` 唯一保证请求重试幂等；重试只返回已有结果，不重复广播大屏。
- 剩余库存由奖品数量减中奖记录实时计算，避免单独库存字段与记录分叉。
- 名单查询使用 `LEFT JOIN` 对缺失的默认名单行按可参加处理，并复用开奖资格条件；名单更新先校验活动用户归属，再以
  `BEGIN IMMEDIATE` upsert 单行状态。
- 连接管理器是单进程实现，多副本部署需后续接入共享消息总线。
