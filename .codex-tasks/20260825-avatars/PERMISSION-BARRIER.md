# 权限屏障与串行降级证据

本任务开始时主 Agent 的文件系统权限为 unrestricted，且工作树含用户既有未提交修改，因此不宣称任何隔离写入或并发只读批次通过。

头像开发、测试、审核均显式降级为 `SERIAL_SHARED_WRITE`，按 TaskGraph 顺序执行；上一节点结束并记录快照后才进入下一节点。审核节点的角色配置为 `sandbox_mode = read-only`，实际执行只读命令，未写入文件或 Git 元数据。主 Agent 在审核前后复核了工作树状态和限定文件清单。

因此 `PERMISSION_NOT_READONLY` 只作为“未启用并发只读批次”的降级依据，不作为串行审核的失败理由；TaskGraph 的 `effective_mode` 和 metrics 均保留该降级事实。
