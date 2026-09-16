# TASK-v1 可验证代码风险咨询

任务：部署包只读风险咨询，不是正式 T6 审核通过。
输入版本：TASK-v1；ARCHITECTURE、DEVELOPMENT、TESTING；HEAD 70793924d129de74b26517a852a1fe6cbe412fc3。
状态：completed
结论：CHANGES_REQUIRED
证据：完整生产差异及新增脚本/测试，40文件清单全部一致，HEAD未变。
变更文件：无。
风险或阻塞：首次连续失败后的重试缺陷；Linux测试门禁仍BLOCKED。
下一步：回退开发修复并补测试，完整Linux证据后才能正式审核验收。

- P2 deploy/scripts/release.sh:105在up前覆盖pending，:62只认可最新两镜像。
  首次失败留下B，无current；重试C在全部替换B前失败，下一次B被误当外来镜像。
  首次无备份无法restore。需受控尝试前驱链或过渡记录，核验service/image/data挂载。
  deploy/tests/test_release_flow.sh:109只测到配置失败，没有覆盖连续两轮失败或B/C混合。
- P3 WIKI.md:183旧start.ps1-Docker描述失效；deploy/tests/AGENTS.md缺四个新测试资产说明。

无其他已确认部署/备份/前端阻断问题。没有隔离worktree或补丁，不宣称并发集成通过。
本次optional咨询独立于正式审核门禁；原生Windows代理、替身、真实临时Git不能代替Linux部署验证。
