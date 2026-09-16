# TASK-v1：Docker Compose 一键部署与升级

任务：将用户批准的部署计划冻结为 T6 交付任务。
输入版本：用户批准计划；HEAD 70793924d129de74b26517a852a1fe6cbe412fc3。
状态：completed
结论：产品定义完成；不代表实现、验证或验收完成。产品原始交接保留于本次任务 product 子 Agent。
证据：现有 Compose 四服务，仅媒体卷；后端 SQLite、已有 /api/v1/health；两个 Router 无 base。
变更文件：无（此文件由主 Agent 记录）。
风险或阻塞：Linux Docker daemon 不可用，实测未完成不得记为 PASS。
下一步：架构方案。

## 目标与范围

Linux git clone 并一次配置后，bash upgrade.sh 自动快进上游、Docker 构建、更新两个服务并检查结果。
宿主机无需 Node/Python；两个运行容器 backend/nginx；仅 Nginx 发布默认 80 可配置端口。
三个 Web 项目构建到 Nginx 镜像 admin/screen/user 目录，锁定 pnpm 依赖，不打包 Electron。
入口 /admin/、/screen/、/user/；根跳管理端，补尾斜杠，各 SPA 独立回退，缺失资源 404。
API /api/ 保留路径及上传/WS；生产同源 /api/v1，按页面协议选择 ws/wss。
适配 Router/build base、二维码和大屏入口；保持显式 URL、本地开发及 Electron 相对资源兼容。
用户端无活动入口显示扫码提示，避免循环重定向；start.ps1 -Docker 随部署入口同步。
独立部署 env 文件忽略 Git；校验管理员密码、JWT、抽奖安全码，拒绝缺失与示例值。
SQLite/媒体统一宿主机持久化并映射 /app/data；忽略镜像上下文中的密钥、数据、Git 和本机产物。
脚本 Bash/LF，可任意目录调用；互斥、检查、快进、构建、配置校验、更新、健康与入口检查。
本地修改/分叉/无上游拒绝；构建配置成功前旧服务保持运行；不 compose down。
镜像按提交标记；更新前停后端备份完整数据，失败恢复旧服务并退出；保留上一成功镜像/配置/备份。
启动或健康失败明确诊断、非零退出；人工恢复配套镜像配置数据，不自动覆盖运行数据。

## 非目标、约束与风险

不安装 Docker，不配置 Git 凭据/HTTPS，不迁移已有服务器，不做零停机/自动数据回滚/业务重构。
允许短暂停机；后端单进程；保持活动隔离，不新增共享业务包。数据一致性、恢复匹配、密钥隔离是 T6 风险。
服务器需要 Linux/Bash/Git/Docker Compose、可访问上游和依赖源、可用端口及足够磁盘。
业务无待确认项。实际 Linux Docker 回归是必需门禁，静态/模拟测试不能替代。
实现前冻结；改变可观察结果须 TASK 新版本，旧测试、审核、验收失效。

## 验收标准（产品交接的完整行为范围）

- AC-001 Given 全新 Linux、已配置且宿主机无 Node/Python，When 任意目录调用 upgrade.sh，Then
  自动部署恰好 backend/nginx 两健康容器；三个站点与 health 可访问，仅 Nginx 发布可配置默认 80，
  Docker 锁定依赖构建且不打包 Electron。
- AC-002 Given 成功部署及活动/用户/数据库/图片且上游可快进，When 升级，Then 发布提交版镜像、
  数据配置保留；构建配置通过前旧服务运行，不 down；切换前停后端完整备份；保留旧镜像/配置/备份。
- AC-003 Given 三端及活动，When 访问根、带/不带斜杠入口、刷新嵌套路径、资源、二维码、大屏，Then
  跳转和独立 SPA 正确、缺失资源 404、活动参数及同源路径正确；显式 URL、本地及 Electron 兼容。
- AC-004 Given HTTP 或外部 HTTPS 代理、管理员及活动用户，When 登录上传读取/聊天/抽奖同步，Then
  同源 API 保留路径、ws/wss 完成真实消息交互、媒体和活动隔离正确。
- AC-005 Given 缺依赖/缺或示例密钥/拉取失败/本地修改/分叉/无上游/构建或配置失败/同时执行，When
  升级，Then 清晰非零退出、不覆盖合并代码、互斥、切换前不影响旧服务、故障消除可重试；密钥和数据隔离。
- AC-006 Given 已成功实例，When 注入备份/启动/健康失败并人工恢复，Then 备份失败恢复旧服务退出，
  其他失败输出阶段诊断、不自动覆盖数据；文档恢复成功；提供失败路径及 Linux 实际构建/升级/恢复证据，
  同步模块 AGENTS/部署及知识文档，未执行明确标记且不算 PASS。

## 流程记录

按产品→架构→开发→测试→审核→验收串行。父权限无法动态收紧，记录 PERMISSION_NOT_READONLY，
不宣称并发资格。不得以环境缺口宣称全部门禁通过。
