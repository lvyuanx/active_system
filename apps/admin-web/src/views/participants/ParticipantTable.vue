<template>
  <div class="participants-table-wrap">
    <el-table
      :data="participants"
      row-key="activity_user_id"
      class="participants-table"
      aria-label="活动参与用户列表"
    >
      <el-table-column label="参与者" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="participant-name">
            <strong>{{ row.username }}</strong>
            <span>ID {{ row.activity_user_id }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" min-width="150" />
      <el-table-column label="加入时间" min-width="180">
        <template #default="{ row }">{{ formatDate(row.joined_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" min-width="150">
        <template #default="{ row }">
          <div class="status-stack">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
              {{ row.is_active ? "正常" : "已停用" }}
            </el-tag>
            <el-tag v-if="row.is_muted" type="warning" effect="plain">已禁言</el-tag>
            <el-tag v-if="row.can_mobile_lottery" type="success" effect="plain">
              移动端可抽奖
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="350" fixed="right">
        <template #default="{ row }">
          <div class="participant-actions">
            <el-button
              text
              :type="row.is_muted ? 'success' : 'warning'"
              :loading="isActionLoading(row.activity_user_id)"
              @click="emit('toggle-mute', row)"
            >{{ row.is_muted ? "解除禁言" : "禁言" }}</el-button>
            <el-button
              text
              :type="row.is_active ? 'danger' : 'primary'"
              :loading="isActionLoading(row.activity_user_id)"
              @click="emit('toggle-active', row)"
            >{{ row.is_active ? "停用" : "恢复" }}</el-button>
            <el-button
              text
              :type="row.can_mobile_lottery ? 'warning' : 'success'"
              :loading="isActionLoading(row.activity_user_id)"
              @click="emit('toggle-mobile-lottery', row)"
            >{{ row.can_mobile_lottery ? "取消移动抽奖" : "授权移动抽奖" }}</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { ActivityParticipant } from "../../api/client";

const props = defineProps<{
  participants: ActivityParticipant[];
  actionParticipantIds: Set<number>;
}>();
const emit = defineEmits<{
  (event: "toggle-mute", participant: ActivityParticipant): void;
  (event: "toggle-active", participant: ActivityParticipant): void;
  (event: "toggle-mobile-lottery", participant: ActivityParticipant): void;
}>();

const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
const isActionLoading = (participantId: number) => props.actionParticipantIds.has(participantId);
</script>

<style scoped>
.participants-table-wrap {
  overflow-x: auto;
}

.participants-table {
  min-width: 980px;
}

.participant-name {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.participant-name strong {
  color: #26332f;
  font-size: 14px;
  font-weight: 650;
}

.participant-name span {
  color: #9aa59f;
  font: 11px Consolas, monospace;
}

.status-stack,
.participant-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.participant-actions {
  justify-content: flex-start;
  gap: 2px;
}
</style>
