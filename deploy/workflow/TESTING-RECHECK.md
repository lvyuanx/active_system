任务：TASK-v1 连续失败重试修复独立复核。
输入版本：TASK-v1；完整读取 DEVELOPMENT-RECHECK.md、RISK-REVIEW.md 与 SUPPLEMENTAL-CHECKS.md；
HEAD 70793924d129de74b26517a852a1fe6cbe412fc3；新清单 development-manifest-v2.json SHA-256
e7123dc5ffea5c2390dad5521f47c4e9619f107aa04c19b206a7c87fc8ce6ba7。
状态：completed
结论：修复范围可执行回归通过；Linux 正式 T6 测试门禁仍 BLOCKED。
证据：flow-1025 的 22 场景输出及 proxy/results.json、新截图；44 个输入文件测试前后哈希一致。
变更文件：仅授权 runtime/test-qa 内 recheck.md、mobile.cjs、mobile_runner.py 与测试临时证据；未改生产或测试资产。
风险或阻塞：原有 Linux Docker、真实 flock、自更新 FD、实际备份恢复运行证据缺口不变。
下一步：提交风险复核；正式测试/审核/验收等待 Linux 证据。

## 命令和独立结论

- `bash deploy/tests/test_release_flow.sh` 退出 0：22 场景通过，证据 flow-1025。
  新 keep-old/mixed 用例确实在 B/C/D 三轮调用生产 deploy_release，不替换该函数或 validate_pending；
  B/C 的替身 up 返回 55，C 记录 pending-parent=B；D 到达 config 并按用例返回 77，证明没有误拒绝
  仍为 B 的容器和 B/C 混合容器。Docker 操作为替身，不能据此证明实际容器发布成功。
  8 个反例直接调用生产 validate_pending，项目/service/image、服务镜像互换、实际挂载、前驱缺失、
  循环、数据目录不一致均非零拒绝；没有放宽验收标准。
- 指定 `QA_MANIFEST=D:/projects/active_system/deploy/runtime/test-dev/development-manifest-v2.json`
  执行 `python deploy/tests/run_proxy_qa.py` 退出 0。原生 Nginx 配置通过；HTTP/HTTPS 三端入口、
  深路由、二维码同源链接、登录注册、上传读取及错误活动拒绝、chat/开奖 ws/wss 全部通过；页面异常 0。
- 使用同一 runner 生命周期执行临时 mobile.cjs，390x844 的 HTTPS /user/ 截图已保存，
  document.scrollWidth=390、innerWidth=390，无横向溢出；人工查看提示文字清晰、无重叠。
  测试命令没有 Python 异常；与它同次执行的无监听 Get-NetTCPConnection 查询造成 shell 返回 1，
  独立后续确认监听数量为 0，不将该查询状态误归为测试失败。
- 后续核对 44 文件 changed_files=0，HEAD 未变，18080/18081/18443 listeners=0。

## AC 与门禁

AC-005/006：连续失败链正向可重试、反向归属拒绝子范围 PASS；Linux 完整范围 BLOCKED。
AC-003：改色后桌面/390px 用户入口及既有代理断言 PASS；完整范围维持此前边界。
AC-001/002/004：本轮代理覆盖结果 PASS，Linux 容器范围仍 BLOCKED。
无变化的 Git 7场景与既有基础验证复用前报告，不重复执行 wheel/Git。
主 Agent 的16 URL、相对screen构建、精简workspace安装见 SUPPLEMENTAL-CHECKS.md，属于上游补充证据，
未冒充本轮独立执行。未修改上游冻结任务单。包级完整门禁与 Linux 集成门禁仍 BLOCKED。
本次为 SERIAL_SHARED_WRITE 的主树开发完成后回归，无隔离 worktree 和补丁集成，补丁 SHA 不适用。
测试写入现已冻结，生产风险复核可继续。
