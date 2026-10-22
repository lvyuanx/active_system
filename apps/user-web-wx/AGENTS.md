# 微信小程序用户端模块说明

## 模块简介

`apps/user-web-wx` 是活动系统的原生微信小程序用户端，用于在微信环境中复刻 `apps/user-web` 的活动参与体验。
工程使用 TypeScript、WXML、WXSS 和微信小程序原生 API，不依赖 Vue、Taro、uni-app 或 Vant Weapp。

## 主要职责

- 解析启动参数或扫码场景中的 `activity_id`。
- 支持入口页调用相机扫描管理员生成的 Web 活动二维码，并从 `/activity/{activity_id}` 路径提取活动 ID。
- 扫描公网二维码后使用二维码来源域名拼接同源 `/api/v1` 和 WebSocket 地址；微信合法域名配置仍由部署环境负责。
- 使用手机号短信验证码完成活动用户登录，并在核验成功后进入独立的首次姓名补充步骤。
- 展示活动首页、抽奖结果、授权抽奖控制、实时聊天室和个人信息。
- 通过 HTTP 和首帧认证 WebSocket 复用现有后端活动、聊天和抽奖协议。
- 在微信安全区、软键盘和窄屏环境下保持移动端布局稳定。

## 目录说明

- `src/pages/entry/`：活动参数提示、活动加载、协议同意、短信登录和姓名补充。
- `src/pages/index/`：兼容旧体验版二维码默认路径的入口跳转页，最终统一进入 `pages/entry/index`。
- `src/pages/legal/`：用户服务协议和隐私政策阅读页，按查询参数展示对应文档。
- `src/pages/activity/`：首页、聊天、抽奖结果、抽奖控制和我的页面。
- `src/components/`：头像和二级页面使用的兼容底部导航。
- `src/custom-tab-bar/`：微信原生 custom tab bar，持久承载首页、聊天和“我的”主导航。
- `src/services/`：HTTP API、活动会话和可重连 WebSocket；socket 服务负责微信任务生命周期、重连和连接错误诊断。
- `src/utils/`：启动参数、token 存储、地址生成、聊天合并、抽奖状态和协议同意逻辑。
- `src/assets/`：ACTIVE Logo、头像、聊天按钮和底部导航图标。

## 核心流程

小程序启动时优先读取 `query.activity_id`，其次读取并解码 `query.scene`。活动 ID 不存在时显示活动入口提示；
存在时先加载公开活动。用户服务协议和隐私政策按版本记录本地同意状态，未同意时不读取活动用户接口，
并禁用手机号、验证码和姓名输入。有效 token 且已同意协议时直接进入首页，失效 token 回到短信登录。
新手机号短信核验成功后由后端签发短期一次性凭证；姓名提交只消费该凭证，不重复调用短信核验服务。返回登录步骤会丢弃凭证并要求重新获取验证码。

主导航使用微信原生 custom tab bar，主 Tab 页面通过 `switchTab` 切换，导航实例不随上方页面重建；页面在 `onShow` 中刷新活动内容。
聊天页先通过 HTTP 游标接口读取历史，再连接 `/chat/ws` 发送首帧认证；重连后用 `after_id` 补齐消息。
抽奖结果页连接公开 `/lottery/ws`，授权抽奖页连接 `/lottery/mobile/ws` 并发送活动用户 token。
微信 `SocketTask` 在 `onOpen` 前可能尚未分配可关闭的 task ID；停止连接时只关闭已建立任务，关闭失败通过 `fail` 回调消费，
避免页面切换或重连期间产生 `closeSocket:fail wcwss taskID not exist` 未处理错误。连接失败会记录不含 token 的 URL 和微信 `errMsg`。

## 配置说明

`src/config.ts` 根据微信运行环境自动选择 development 和 production 地址。小程序正式运行必须使用 HTTPS API 和 WSS，
并将对应域名加入微信公众平台的 request、download 和 socket 合法域名。开发者工具本地联调可关闭合法域名校验。
`app.json` 显式开启 `__usePrivacyCheck__`；发送验证码、短信登录和首次姓名提交前还会调用
`wx.requirePrivacyAuthorize`，因此发布前必须在微信公众平台完成真实的“小程序用户隐私保护指引”配置。

## 扩展方式

- 新增活动接口时在 `src/types/api.ts` 和 `src/services/api.ts` 中分别增加类型与请求函数。
- 新增实时事件时优先扩展 `src/utils/lottery.ts` 或聊天纯逻辑工具，再接入页面消息处理。
- 新增主 Tab 页面时接入 `app.json` 的 tabBar 页面列表和 `custom-tab-bar`，不要在主 Tab 页面重复渲染 `activity-tabbar`。
- 抽奖结果和抽奖控制等二级页面可以继续使用 `activity-tabbar` 兼容入口，并通过 `switchTab` 返回主 Tab。

## 注意事项

- token 必须使用 `active_user_token:{activity_id}`，不能改成全局单 token。
- 用户协议同意状态使用 `src/utils/privacy.ts` 中的版本号；协议内容、版本或处理目的变化时必须提升版本，
  让小程序重新取得用户同意。
- 任何发送短信、短信登录、首次姓名提交或读取活动用户信息的入口都必须经过协议同意检查；协议阅读页通过
  `pages/legal/index?type=service|privacy` 打开。
- 活动数据、聊天消息和抽奖消息都必须保留 `activity_id` 上下文。
- 聊天历史加载只允许使用 `before_id`，重连补齐只允许使用 `after_id`，并需按 `message_id` 去重。
- 抽奖控制必须保持开始、停止、开奖三阶段协议，不得改成单次请求直接开奖。
- 修改页面后需在微信开发者工具和 320px 至 430px 宽度范围检查安全区、软键盘和底部导航。
- 聊天页输入区的底部预留必须包含自定义 Tabbar 高度和 `safeAreaBottom`；键盘显示时隐藏 Tabbar 并清零该预留，恢复时重新占位。
- 聊天表情和发送按钮的禁用态使用独立深灰 SVG 图标，并分别设置按钮背景和边框，不能只给整个按钮设置统一透明度，避免白色图标与灰色背景对比不足。
- 聊天表情抽屉使用四列 CSS Grid；表情格子必须设置 `width: 100%` 和 `min-width: 0`，不能依赖窄屏下的 flex 百分比宽度计算。
- 表情抽屉只允许纵向滚动，容器和格子必须限制为 `max-width: 100%` 并隐藏横向溢出，避免窄屏下出现横向滚动条。
- 结构型可点击行使用 `view` 配合 `bindtap`；需要表单或辅助功能语义时才使用原生 `button`，并通过全局 WXSS 重置按钮默认外观。
