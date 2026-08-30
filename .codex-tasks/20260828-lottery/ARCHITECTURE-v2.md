# ARCHITECTURE-v2：抽奖名单弹窗化与服务端分页

## 方案

抽奖主配置只负责奖项、奖品和规则；名单通过管理员 HTTP 接口按需读取。`lottery_entries` 继续只保存黑名单/白名单覆盖状态，缺少记录时通过 `LEFT JOIN` 按默认值处理，不再在配置读取时为活动全量补行。

## 接口

- `GET /admin/activities/{activity_id}/lottery` 返回奖项、奖品、规则和 `entry_summary`，不返回 `entries`。
- `GET /admin/activities/{activity_id}/lottery/entries?keyword=&status=all&page=1&page_size=20` 返回当前页、总数、是否还有下一页和统计摘要。
- `PUT /admin/activities/{activity_id}/lottery/entries/{activity_user_id}` 接收完整黑白名单状态，返回规范化用户行和最新摘要。
- `status` 固定为 `all`、`eligible`、`blacklisted`、`whitelisted`、`inactive`；可抽奖条件复用开奖事务中的停用、黑白名单、跨奖品不重复逻辑。

## 数据与并发

- 名单更新使用 `BEGIN IMMEDIATE`，先验证活动用户归属，再执行 upsert；黑白名单互斥由模型和服务层双重校验。
- 配置保存不再接收或替换全量名单，避免分页页面提交局部数据时删除未显示用户。
- 增加活动手机号查询索引；用户名沿用现有活动索引。

## 管理端流程

主页面展示统计卡片和“配置黑白名单”按钮。弹窗打开时重置筛选并加载第一页；搜索提交、筛选切换、分页切换均只请求当前页。开关请求完成后重新加载当前页，若当前页因筛选变化为空则回退到上一页；请求失败保留服务端原值并提示。

## 风险控制

接口继续使用现有 `require_superuser`；手机号只出现在管理员 HTTP 响应，不进入公开快照或大屏事件。开奖 WebSocket、公开脱敏协议和跨活动房间广播不变。

