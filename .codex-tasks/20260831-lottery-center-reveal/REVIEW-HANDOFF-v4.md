任务：抽奖进行中标签展示奖品图片
输入版本：TASK-v3；测试输入：TESTING-HANDOFF-v4
状态：completed
结论：APPROVED
证据：

- 图片来源限定为已存在的公开 `LotterySnapshot.awards[].prizes[].image_url`，按 `award_id` 和 `prize_id` 关联，不扩大轮次协议或暴露存储 key。
- 图片展示复用现有 API origin 解析、失败集合和文本回退，不影响开奖状态、球体动画或中奖揭晓层。
- CSS 以缩略图固定尺寸和 flex 文本截断保持标签边界，移动端有独立尺寸规则；自动化测试、类型检查、构建和 diff 校验均通过。

变更文件：审核未修改文件。
风险或阻塞：未发现阻断问题；真实活动进行中标签截图仍属于发布前视觉覆盖缺口。
下一步：按 TASK-v3 逐条执行用户场景验收。
