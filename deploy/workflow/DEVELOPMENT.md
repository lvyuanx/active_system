# TASK-v1 开发交接

任务：实现 Docker Compose 一键部署升级及人工恢复。
输入版本：TASK-v1、ARCHITECTURE.md；HEAD 70793924d129de74b26517a852a1fe6cbe412fc3，结束未变。
状态：completed
结论：开发与基础验证完成，可独立测试；不代表 T6 验收通过。
证据：三端类型检查/子路径生产构建、后端 wheel、Compose config、Bash语法、配置解析及归档测试通过。
变更文件：40文件，完整路径与SHA-256见 deploy/runtime/test-dev/development-manifest.json。
风险或阻塞：Linux Docker daemon不可用，真实容器构建/升级/WS业务/恢复未验证。
下一步：独立测试；测试通过才能进入正式审核及验收。

## 完整岗位交接

工作包 deployment-serial，路径 D:/projects/active_system，SERIAL_SHARED_WRITE；无detached隔离，
未提交/派生/改Git元数据。主Agent新增workflow不属于开发文件。
清单SHA256：73c096e63f3f81382669c55d670a90edc6ff4ac648fa0c569bca5d636dd74b64。
两个运行服务，Docker内锁定pnpm构建三Web，独立子路径和同源API/ws/wss。
升级固定锁/字面env/上游快进/自更新续跑/唯一镜像tag+实际ID；停旧后端完整备份，失败恢复旧后端。
首次失败通过pending镜像记录重试；已有成功记录时backend镜像不一致要求人工恢复，避免数据错配。
恢复校验归档，写新目录，保留失败现场，成功推进current供以后升级使用。
修复setuptools包发现，不改后端业务。同步模块AGENTS、README、MEMORY、LEARNING、WIKI；CLAUDE合规未改。

## AC与基础验证

- AC-001：Compose/Dockerfile/upgrade；三端类型build、wheel、Compose配置通过。
- AC-002：release/artifacts；归档测试通过，真实升级待测。
- AC-003：Router/app-links/Nginx/entry；子路径构建通过，浏览器待测。
- AC-004：API/Nginx；类型通过，真实登录上传/WS待测。
- AC-005：common/pending；语法/配置拒绝通过，完整故障替身待测。
- AC-006：restore/说明；归档校验/拒覆盖/路径安全通过，Linux恢复待测。

实际命令退出码：三端 `pnpm --filter @active/<app> exec vue-tsc --noEmit` 均0；
三端 `vite build --base=/admin/`、`/user/`、`/screen/` 均0；
`python -m pip wheel --no-deps ./apps/backend --wheel-dir deploy/runtime/test-dev/wheels` 0；
四Shell `bash -n` 均0；`bash deploy/tests/test_settings.sh` 0；
`python -m unittest discover -s deploy/tests -p test_artifacts.py -v` 0，3tests；
独立测试变量 `docker compose ... config --quiet` 0；`git diff --check` 0。
先前 no-build-isolation wheel 因本机缺 bdist_wheel 失败，隔离构建随后成功。
方案偏差：安全逐文件复制恢复，兼容旧Python3.11，不依赖新tarfile.filter。
没有生成补丁/intent-to-add；串行共享树无需隔离集成补丁。
