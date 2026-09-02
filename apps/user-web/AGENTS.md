# 用户端模块说明

用户端使用 Vue 3 + Vant 4，面向移动端活动参与者，负责活动入口、报名参与、结果查看和个人信息。页面放在 src/views/，移动端通用交互组件放在 src/components/。

## 当前已实现功能

- src/views/activity/：活动级入口页，按活动 ID读取公开信息、注册/登录并展示活动首页。
- src/views/activity/activity.css、chat.css、activity-auth.css：活动入口专属视觉样式，分别负责页面公共、聊天页和认证页的黑金主题、Vant 覆盖、移动断点与安全区适配。
- src/api/client.ts：活动公开详情、活动用户注册/登录、缓存 token 校验接口。
- src/components/ActivityAvatar.vue 与 src/assets/avatars/：受信任的二十款本地卡通静态 SVG 头像映射和展示封装。
- 活动用户 token 使用 active_user_token:{activity_id} 本地存储键，活动之间相互隔离。
- 登录后的活动壳不渲染全局顶部 NavBar，通过顶部 safe-area 直接展示首页、聊天、我的三个嵌套路由；
  底部 Tabbar 使用命名路由持续匹配当前项，当前项以金色图标、金色加粗文字和包裹背景高亮。
- 聊天页使用 HTTP 历史游标和首帧认证 WebSocket，
  断线按指数退避重连并以 after_id 补齐消息；登录后读取当前活动启用表情，点击表情立即发送 sticker-only 消息；消息行以发送者用户名、头像和左右气泡展示，
  消息列表仅在追加前位于底部阈值内时自动滚动；输入框默认一行且与发送按钮同高，最多可视三行，超过三行后在控件内部滚动。
- 聊天 WebSocket 收到停用用户的 `unauthorized` 错误后会清除当前活动 token、停止重连并返回活动入口；`muted` 错误只提示用户，不清除会话。
- `views/activity/home.vue` 和 `views/activity/me.vue` 展示当前活动用户头像；
  `views/activity/me.vue` 仍仅清除当前活动 token，展示活动用户稳定 ID 与加入时间。

活动入口只提供“登录并进入”活动按钮：先使用用户名和手机号登录，接口返回未认证时自动注册新用户；手机号已被其他用户名使用时显示后端冲突提示。

活动入口页使用 Vant 4 移动端组件体系：CellGroup、Cell、Form、Field、Button、Tag、Icon、Loading 和 Tabbar。
认证页保留 B 方案的金线活动入口标题、居中圆环 A 标识、活动上下文、登录标题、独立字段信息流和单一金色主操作；
登录后展示活动状态、欢迎摘要和现有服务入口。

页面通过活动页命名空间样式统一控制炭黑/深灰表面、哑金品牌色以及成功和结束状态色。
页面按手机宽度流式布局，并使用固定触控尺寸、长文本换行、聚焦反馈和 reduced-motion 规则；
顶部和底部保留 safe-area inset，桌面预览限制在 600px 内。

头像组件只从二十个静态 SVG 导入中按 `avatar_id` 映射资源，不接受路径或 HTML；头像显示在首页、“我的”页和消息行中，
消息行头像使用稳定的活动用户 ID 本地映射，不进入聊天消息或 WebSocket 协议。

聊天表情图片由后端提供活动隔离的版本化 URL；表情气泡和表情选择器使用图片渲染，图片失败时显示 `[表情] 名称`。
表情消息不与文字草稿混合，活动关闭、结束、禁言或停用时沿用现有发送限制。
聊天输入区使用圆形按钮承载用户提供的白色 SVG：笑脸图标放大显示并打开表情包选择器，纸飞机图标提交文本消息；按钮保持固定触控尺寸并提供无障碍标签。
表情包选择器在点击输入框、聊天输入区域外或按 `Escape` 时自动隐藏，点击表情按钮可再次切换显示。
表情包请求完成且列表为空时在选择器内显示“暂无表情”，请求进行中显示“正在加载表情”。

聊天输入框保留 `maxlength=500` 限制，但不显示会撑高默认输入框的字数提示；Vant Field 使用零垂直内边距和内容居中对齐，并关闭聊天 Field 默认的内部 `::after` 分隔线。

登录后活动壳使用 `activity-shell` 承接顶部 safe-area；聊天高度只扣除 Tabbar 与上下 safe-area，
不再扣除已删除的 52px NavBar。Tabbar 自身负责底部 safe-area，导航项不重复添加 inset。

index.html 必须保留 width=device-width、initial-scale=1 和 viewport-fit=cover，避免设备模拟器使用桌面布局视口缩放页面。

活动认证页使用 src/assets/active-logo.png 的圆环 A 黑金标识。
