# 活动模块说明

## 模块简介

`activities` 提供管理员活动创建、查询和生命周期状态转换接口，并负责在活动创建事务中建立活动级基础配置。

## 目录说明

- `router.py`：活动请求模型、管理员 CRUD/状态转换、小程序码路由和活动记录转换逻辑。
- `mini_code.py`：调用微信接口获取 access_token 和活动专属小程序码，进程内缓存 access_token。

## 主要流程

管理员创建活动时，后端在同一 SQLite 事务中写入 `activities` 记录，并初始化弹幕模块的默认配置和 `token_version=1`。
这样活动创建完成后即可拥有稳定 token；弹幕模块仍会对历史活动执行兼容性按需补齐。

管理员通过 `GET /api/v1/admin/activities/{activity_id}/mini-code` 获取活动专属 PNG 小程序码。
小程序码目标为 `pages/entry/index?activity_id={activity_id}`，由小程序入口读取活动参数后直接加载活动。

## 数据隔离

所有活动查询、状态变更和基础配置初始化均使用当前 `activity_id`，不得跨活动复用配置记录。

## 注意事项

- 新活动初始状态为 `closed`。
- 只有显式生命周期接口可以切换活动状态，`ended` 活动不可恢复。
- 弹幕 token 仅由弹幕模块生成；活动模块只触发默认记录初始化，不直接组装 token 字符串。
- 小程序码接口只允许超级管理员访问；`WECHAT_MINIAPP_SECRET` 仅由后端使用，不得返回前端或写入日志。
- `WECHAT_MINIAPP_PAGE` 必须是已发布的小程序页面路径，默认是 `pages/entry/index`。
