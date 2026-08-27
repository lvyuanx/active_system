# TASK-v4 浏览器证据

测试页面：`http://localhost:5175/activity/41f9d161-c015-42d4-a4f5-0cc65ecec285/chat`

## 430×932

- `activity-nav` 存在，聊天子页 `chat-header`、`chat-connection`、`chat-composer-identity` 均不存在。
- `chat-content`：top=53、bottom=873；消息列表 top=73、bottom=795；composer top=795、bottom=873；Tabbar top=873、bottom=932。
- 消息行实际显示头像、真实用户名、时间和气泡；他人消息左侧，本人消息右侧。
- 输入框 field bottom=865，发送按钮 bottom=865；页面无横向溢出。

截图：[BROWSER-430x932-v4.png](BROWSER-430x932-v4.png)

## 390×450

- `activity-nav`：top=0、bottom=53；聊天壳：top=53、bottom=391；Tabbar：top=391、bottom=450。
- 三个待移除区域均不存在；消息列表 top=73、bottom=313；空输入框 field bottom=383，发送按钮 bottom=383；页面宽度 390，`documentWidth=390`。
- 三行输入后 textarea height=72、scrollHeight=72，field/send bottom=383；第四行输入后 textarea height=72、scrollHeight=96，第四行值仍保留，页面无横向溢出。

截图：[BROWSER-390x450-v4.png](BROWSER-390x450-v4.png)

## 实时滚动正反向

- 列表顶部：追加合成消息“最终顶部回归”前 `scrollTop=0`、`maxScrollTop=1319`；追加后 `scrollTop=0`、`maxScrollTop=1346`，消息实际渲染且为本人消息。
- 列表底部：追加合成消息“最终底部跟随”前 `scrollTop=1346`；追加后 `scrollTop=1422`、`maxScrollTop=1422`、`atBottom=true`，消息实际渲染。
- 合成消息只写入本地开发数据库用于回归，不包含真实个人数据。

## 证据来源

- 浏览器 DOM snapshot、页面 `evaluate` 的只读尺寸/节点检查和截图均在当前 v4 CSS 拆分后重新执行。
- 页面使用本地合成测试用户；未修改 HTTP/WebSocket payload。
