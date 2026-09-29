<template>
  <div class="activity-management">
    <ActivitySidebar
      :activity="activity"
      :activity-id="activityId"
      active="participants"
      :username="username"
    />

    <section class="workspace">
      <header class="workspace-topbar">
        <div class="breadcrumb">
          <span>活动管理</span><b>/</b><span>参与者</span><b>/</b>
          <strong>{{ activity?.name || "加载中" }}</strong>
        </div>
        <span
          class="workspace-status"
          :class="activity ? `workspace-status--${activity.status}` : ''"
        >
          <i aria-hidden="true"></i>{{ activity ? statusLabel(activity.status) : "正在加载" }}
        </span>
      </header>

      <main class="management-page">
        <el-alert
          v-if="error"
          :title="error"
          type="error"
          show-icon
          closable
          class="page-alert"
          @close="error = ''"
        />
        <el-skeleton v-if="loading" :rows="10" animated />

        <template v-else-if="activity">
          <section class="activity-titlebar">
            <div>
              <p class="eyebrow">PARTICIPANT MANAGEMENT</p>
              <h1>参与者</h1>
              <p class="activity-meta">
                {{ activity.name }} · 共 {{ participants.length }} 位参与用户
              </p>
            </div>
            <span class="status-badge" :class="`status-badge--${activity.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
            </span>
          </section>

          <section class="content-surface participants-surface">
            <header class="content-heading">
              <div>
                <p class="eyebrow">ACTIVITY PARTICIPANTS</p>
                <h2>参与用户 <span class="count-badge">{{ participants.length }}</span></h2>
              </div>
              <span class="content-hint">状态变更会立即生效</span>
            </header>

            <div v-if="!participants.length" class="empty-state">
              <span class="empty-mark">○</span>
              <h3>暂时还没有参与用户</h3>
              <p>用户通过活动入口完成登录后，会出现在这里。</p>
            </div>

            <div v-else class="participants-table-wrap">
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
                        @click="toggleMute(row)"
                      >{{ row.is_muted ? "解除禁言" : "禁言" }}</el-button>
                      <el-button
                        text
                        :type="row.is_active ? 'danger' : 'primary'"
                        :loading="isActionLoading(row.activity_user_id)"
                        @click="toggleActive(row)"
                      >{{ row.is_active ? "停用" : "恢复" }}</el-button>
                      <el-button
                        text
                        :type="row.can_mobile_lottery ? 'warning' : 'success'"
                        :loading="isActionLoading(row.activity_user_id)"
                        @click="toggleMobileLottery(row)"
                      >{{ row.can_mobile_lottery ? "取消移动抽奖" : "授权移动抽奖" }}</el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute } from "vue-router";
import {
  changeActivityParticipant,
  getActivity,
  listActivityParticipants,
  type Activity,
  type ActivityParticipant,
  type ParticipantAction,
} from "../../api/client";
import ActivitySidebar from "../../components/ActivitySidebar.vue";

const route = useRoute();
const activityId = String(route.params.activityId);
const activity = ref<Activity>();
const participants = ref<ActivityParticipant[]>([]);
const loading = ref(true);
const actionParticipantIds = ref(new Set<number>());
const error = ref("");
const username = localStorage.getItem("active_admin_username") || "超级用户";

const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
const isActionLoading = (participantId: number) => actionParticipantIds.value.has(participantId);

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [currentActivity, currentParticipants] = await Promise.all([
      getActivity(activityId),
      listActivityParticipants(activityId),
    ]);
    activity.value = currentActivity;
    participants.value = currentParticipants;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "参与者加载失败";
  } finally {
    loading.value = false;
  }
};

const updateParticipant = async (participant: ActivityParticipant, action: ParticipantAction) => {
  const participantId = participant.activity_user_id;
  actionParticipantIds.value = new Set(actionParticipantIds.value).add(participantId);
  try {
    const updated = await changeActivityParticipant(activityId, participantId, action);
    const index = participants.value.findIndex(
      (item) => item.activity_user_id === participantId,
    );
    if (index >= 0) participants.value[index] = updated;
    const messages: Record<ParticipantAction, string> = {
      mute: "参与者已禁言",
      unmute: "参与者已解除禁言",
      deactivate: "参与者已停用",
      activate: "参与者已恢复",
      "mobile-lottery/grant": "已授权移动端抽奖",
      "mobile-lottery/revoke": "已取消移动端抽奖权限",
    };
    ElMessage.success(messages[action]);
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "操作失败，请稍后重试");
  } finally {
    const pending = new Set(actionParticipantIds.value);
    pending.delete(participantId);
    actionParticipantIds.value = pending;
  }
};

const toggleMute = async (participant: ActivityParticipant) => {
  const action: ParticipantAction = participant.is_muted ? "unmute" : "mute";
  if (action === "mute") {
    try {
      await ElMessageBox.confirm(
        `确定禁言参与者“${participant.username}”吗？禁言后仍可查看聊天，但不能发送消息。`,
        "确认禁言",
        { confirmButtonText: "确认禁言", cancelButtonText: "取消", type: "warning" },
      );
    } catch {
      return;
    }
  }
  await updateParticipant(participant, action);
};

const toggleActive = async (participant: ActivityParticipant) => {
  const action: ParticipantAction = participant.is_active ? "deactivate" : "activate";
  if (action === "deactivate") {
    try {
      await ElMessageBox.confirm(
        `确定停用参与者“${participant.username}”吗？停用会立即使其当前登录失效。`,
        "确认停用",
        { confirmButtonText: "确认停用", cancelButtonText: "取消", type: "warning" },
      );
    } catch {
      return;
    }
  }
  await updateParticipant(participant, action);
};

const toggleMobileLottery = async (participant: ActivityParticipant) => {
  const action: ParticipantAction = participant.can_mobile_lottery
    ? "mobile-lottery/revoke"
    : "mobile-lottery/grant";
  await updateParticipant(participant, action);
};

onMounted(load);
</script>

<style scoped>
.activity-titlebar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin: 0 8px 22px;
}

.activity-titlebar h1,
.content-heading h2 {
  margin: 0;
}

.activity-titlebar h1 {
  font-size: 27px;
}

.activity-meta {
  margin: 9px 0 0;
  color: #849089;
  font: 12px Consolas, monospace;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #21588f;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}

.status-badge i {
  width: 7px;
  height: 7px;
  background: #2e73b8;
  border-radius: 50%;
}

.status-badge--open {
  color: #0f7656;
}

.status-badge--open i {
  background: #159a70;
}

.status-badge--ended {
  color: #a8403b;
}

.status-badge--ended i {
  background: #d35c55;
}

.participants-surface {
  min-height: 430px;
  padding: 28px 30px 30px;
  background: #fff;
  border: 1px solid #dfe5e2;
  border-radius: 12px;
  box-shadow: 0 8px 26px rgb(31 48 41 / 5%);
}

.content-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.content-heading h2 {
  font-size: 22px;
}

.content-hint {
  color: #849089;
  font-size: 12px;
}

.count-badge {
  display: inline-grid;
  place-items: center;
  min-width: 24px;
  height: 22px;
  margin-left: 5px;
  padding: 0 6px;
  color: #0f6652;
  background: #e4f3ee;
  border-radius: 11px;
  font-size: 12px;
  vertical-align: 2px;
}

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

.empty-state {
  padding: 70px 24px 82px;
  text-align: center;
}

.empty-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin: 0 auto 18px;
  color: #147d64;
  background: #e3f1ed;
  border: 1px solid #c7e3db;
  border-radius: 6px;
  font-size: 24px;
}

.empty-state h3 {
  margin: 0;
  font-size: 18px;
}

.empty-state p {
  margin: 9px 0 0;
  color: #718078;
  font-size: 14px;
}

@media (max-width: 800px) {
  .activity-titlebar,
  .content-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .participants-surface {
    padding: 22px 18px;
  }
}
</style>
