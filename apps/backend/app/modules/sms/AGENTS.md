# 短信模块说明

## 模块简介

`apps/backend/app/modules/sms` 负责活动入口的短信验证码发送、核验和手机号级发送频控。

## 主要职责

- 校验中国大陆手机号并确认活动存在。
- 调用阿里云号码认证服务 `SendSmsVerifyCode` 发送验证码。
- 调用阿里云号码认证服务 `CheckSmsVerifyCode` 核验验证码。
- 使用 SQLite 持久化手机号发送时间，按手机号全局限制每 60 秒一次。
- 不保存或返回验证码，验证码由阿里云生成。

## 目录说明

- `router.py`：公开短信验证码发送、核验接口和请求/响应模型。
- `service.py`：阿里云 SDK 调用、请求参数组装、核验结果解析和数据库限流。

## 核心接口

`POST /api/v1/activities/{activity_id}/auth/sms-code` 接收 `phone`，成功返回验证码有效期和下一次可发送间隔。
接口不要求登录，但活动必须存在。

`POST /api/v1/activities/{activity_id}/auth/sms-code/verify` 接收 `phone` 和 4–8 位数字 `code`。
阿里云返回 `PASS` 时响应 `verified=true`，返回 `UNKNOWN` 时响应 `verified=false`，两者均为 HTTP 200。

## 数据流

请求先校验配置和手机号，再在 `sms_verification_sends` 中通过 `BEGIN IMMEDIATE` 原子预约发送时间，随后调用阿里云。
限流记录按手机号跨活动共享；阿里云请求失败时仍保留预约时间，避免不确定的网络结果导致重复发送。
核验请求不写入本地数据库，直接使用与发送时一致的 `SchemeName` 调用阿里云并解析 `Model.VerifyResult`。

## 配置说明

阿里云凭据由默认凭据链读取。签名、模板、Endpoint、方案名、验证码长度和有效期由 `ALIYUN_SMS_*` 环境变量配置。

## 注意事项

- 不要在接口响应、日志或异常详情中暴露验证码、AccessKey 或阿里云原始响应。
- `TemplateParam` 使用 `##code##`，核验必须使用阿里云返回的 `Model.VerifyResult`，不能只判断顶层 `Code=OK`。
