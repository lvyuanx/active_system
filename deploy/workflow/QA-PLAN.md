# TASK-v1 测试准备

测试必须等待开发交接后进行；本文件不代表用例执行或通过。

## 可用工具

- Git Bash：D:/services/Git/bin/bash.exe（无 flock；替身只验证控制流，不代表内核锁验证）。
- Nginx：C:/Users/Administrator/AppData/Local/Temp/active-system-nginx-check/nginx-1.28.3/nginx.exe。
- 临时测试证书：同目录上一级 test.crt、test.key，私钥仅用于本机两天有效的自签测试。
- Playwright：C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright。
- 浏览器：C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1187/chrome-win/chrome.exe。
- 上述浏览器启动已通过。Python httpx/PIL/pytest 可用。Linux Docker 不可用。

## 独立本机代理回归

可将三端生产构建复制到测试临时目录的 admin/screen/user，复制生产 Nginx location 配置，
仅替换 root、listen 80 为18080、backend:8000为127.0.0.1:18081，外层增加 events/http。
后端用全套测试环境变量启动 uvicorn，数据库/media 指向独立临时目录，不使用根.env凭据。
可增加18443自签TLS server代理18080，保留Host并设置X-Forwarded-Proto/Upgrade。

浏览器和HTTP验证根/尾斜杠、三端、用户扫码提示、嵌套路由刷新、缺失资源404、请求无localhost:8000、
管理员登录建活动生成同源用户/大屏链接、用户报名、图片上传读取、聊天及开奖WS同步。
HTTPS上下文忽略本机自签证书并断言wss。保存截图与测试摘要，停止本次专属进程。
此结果只证明本机生产配置适配后的代理行为，不是Linux容器实测。

## 脚本风险

临时Git仓库与Docker命令替身验证env拒绝/不泄密、快进/超前/分叉/无上游/脏树/拉取失败，
构建与配置失败不stop/up，resume脚本更新、pending首次失败重试、成功记录镜像不一致拒绝，
备份失败恢复、启动失败current不变、恢复不会覆盖原目录。禁止用替身结果代替真实锁/容器/备份门禁。
Python备份工具可用真实临时归档单测：完整性、校验损坏、链接/逃逸拒绝、目标非空拒绝、配置挂载更新。

## 交接

每个AC分别列实际已执行子场景和Linux待验证场景；必需Linux场景缺失时状态blocked，
禁止把T6验收写成通过。测试角色仅写测试、夹具及测试报告，生产问题返回开发。
