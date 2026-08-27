# TASK-v7 浏览器证据

## 恢复记录

初始 Browser runtime 在测试子线程中没有可用浏览器；主线程随后取得 In-app Browser 绑定。
既有 5175 服务只监听 IPv6 回环，In-app Browser 对 `127.0.0.1:5175` 返回连接拒绝，因此新增仅用于
验收的 IPv4 实例：前端 `192.168.18.187:5177`、后端 `192.168.18.187:8002`。这两个实例不替换或停止
原有 5175/8000 服务，测试完成后由主线程清理。

## 认证页，430x932

- URL：`/activity/41f9d161-c015-42d4-a4f5-0cc65ecec285`。
- 实际截图显示活动标识、活动上下文、登录标题、用户名和手机号输入框。
- DOM 测量：`loginHeroCount=1`、`headerCount=0`；`login-hero` 宽 `360px`，x=`35px`；
  登录表单宽 `360px`，x=`35px`。
- 结论：认证页自身 `login-hero` 保留，登录后活动壳 Header 不会影响认证页。

## 有效会话，430x932

复用现有合成账号登录后，首页、聊天和“我的”页均有 `headerCount=0`。

| 页面 | 路径 | 唯一 active 项 | 关键实测 |
| --- | --- | --- | --- |
| 首页 | `/activity/:activityId` | 首页 | Tabbar y=`874px`，高=`58px`；首页主体 y=`0px`，高=`932px`。 |
| 聊天 | `/activity/:activityId/chat` | 聊天 | chat y=`0px`，高=`874px`；composer 底=`874px`，与 Tabbar 顶相邻。 |
| 我的 | `/activity/:activityId/me` | 我的 | Tabbar y=`874px`，高=`58px`；主体没有旧 Header 占位。 |

首页 active 项的实际计算样式：

- 图标和文字颜色：`rgb(231, 202, 134)`。
- 字重：`700`。
- 背景：`rgba(213, 179, 107, 0.14)`。
- 边框：`rgba(213, 179, 107, 0.42)`。

inactive 项的文字/图标颜色为 `rgb(143, 145, 141)`、字重 `400`，背景及边框透明。
首页与聊天截图均显示选中项有金色文字、图标和圆角背景包裹。

## 路由交互

- 点击首页后聊天：URL 为 `/chat`，仅聊天项 active。
- 点击聊天后“我的”：URL 为 `/me`，仅“我的”项 active。
- Back：回到 `/chat`，仅聊天项 active。
- Forward：回到 `/me`，仅“我的”项 active。
- 直接访问并等待活动壳挂载：首页、聊天、“我的”均各有一个对应 active 项。
- 刷新聊天与“我的”：各自的 active 项保持正确。

## 聊天输入框

### 430x932

- 默认：Field=`44px`，发送按钮=`44px`，两者底部均为 y=`866px`。
- 四行文本：textarea `clientHeight=72`、`scrollHeight=96`；Field=`74px`，composer 底仍为
  y=`874px`，不与 Tabbar 重叠。

### 390x450

- 默认：chat 高=`392px`，消息区 y=`20px` 到 y=`332px`，composer y=`332px` 到 y=`392px`，
  Tabbar y=`392px` 到 y=`450px`；Field/按钮均=`44px`。
- 四行文本：textarea `clientHeight=72`、`scrollHeight=96`；Field y=`310px` 到 y=`384px`，
  composer y=`302px` 到 y=`392px`，Tabbar 顶仍为 y=`392px`；发送按钮可见。
- 实际短屏截图显示四行文本仅可见三行，textarea 内部出现滚动条，Tabbar 没有遮挡输入区或发送按钮。

## 运行状况与数据影响

- 页面控制台 warning/error 筛选为空。
- 聊天历史消息、头像、用户名和气泡已在实际聊天页渲染；没有发送新消息。
- 登录使用已有合成账号；没有创建用户、修改活动数据或安装请求拦截。
