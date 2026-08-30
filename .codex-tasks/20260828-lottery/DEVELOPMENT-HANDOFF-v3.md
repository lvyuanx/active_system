任务：抽奖奖项与奖品树形编辑
输入版本：TASK-v3
状态：completed
结论：已将管理端奖项和奖品改为父子树形编辑；后端请求格式、库存规则和开奖协议保持不变。
证据：
- `apps/admin-web/src/views/lottery/index.vue` 按奖项节点分组渲染 `prizesForAward(award)`，新增奖品接收当前奖项参数，不再显示所属奖项下拉框。
- 新增奖项没有 `award_id` 时显示“待保存”、禁用“添加奖品”；删除奖项会同步移除本地对应子奖品，避免提交悬空关联。
- 右侧开奖选择器只使用 `savedPrizes`，未保存奖品不会生成空值选项。
- `apps/admin-web/src/views/lottery/lottery.css` 增加节点层级线、父子节点背景和窄屏布局。
变更文件：`apps/admin-web/src/views/lottery/index.vue`；`apps/admin-web/src/views/lottery/lottery.css`；`apps/admin-web/src/views/lottery/AGENTS.md`；`apps/admin-web/src/views/lottery/TASK-v3.md`
风险或阻塞：无；树形视图仍在保存时转换为既有 `awards` 和 `prizes` 数组。
下一步：进入测试、审核和验收门禁。

