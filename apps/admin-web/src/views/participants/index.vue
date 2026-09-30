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
                {{ activity.name }} · {{ participantCountLabel }}
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
                <h2>参与用户 <span class="count-badge">{{ total }}</span></h2>
              </div>
              <span class="content-hint">状态变更会立即生效</span>
            </header>

            <div class="participants-toolbar">
              <div class="participant-search-row">
                <el-input
                  v-model="keywordInput"
                  clearable
                  placeholder="搜索用户名或手机号"
                  @keyup.enter="searchParticipants"
                  @clear="searchParticipants"
                />
                <el-button
                  type="primary"
                  :loading="participantsLoading"
                  @click="searchParticipants"
                >
                  搜索
                </el-button>
              </div>
            </div>

            <div v-loading="participantsLoading" class="participants-results">
              <div v-if="!participants.length" class="empty-state">
                <span class="empty-mark">○</span>
                <h3>{{ keyword ? "没有匹配的参与用户" : "暂时还没有参与用户" }}</h3>
                <p>
                  {{
                    keyword
                      ? "请尝试其他用户名或手机号。"
                      : "用户通过活动入口完成登录后，会出现在这里。"
                  }}
                </p>
              </div>

              <ParticipantTable
                v-else
                :participants="participants"
                :action-participant-ids="actionParticipantIds"
                @toggle-mute="toggleMute"
                @toggle-active="toggleActive"
                @toggle-mobile-lottery="toggleMobileLottery"
              />

              <div v-if="total" class="participants-footer">
                <span>{{ rangeLabel }}</span>
                <el-pagination
                  v-model:current-page="page"
                  v-model:page-size="pageSize"
                  background
                  layout="total, sizes, prev, pager, next"
                  :page-sizes="[20, 50, 100]"
                  :total="total"
                  @current-change="loadParticipants"
                  @size-change="changePageSize"
                />
              </div>
            </div>
          </section>
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute } from "vue-router";
import {
  changeActivityParticipant,
  getActivity,
  listActivityParticipants,
  type Activity,
  type ActivityParticipant,
  type ActivityParticipantPage,
  type ParticipantAction,
} from "../../api/client";
import ActivitySidebar from "../../components/ActivitySidebar.vue";
import ParticipantTable from "./ParticipantTable.vue";

const route = useRoute();
const activityId = String(route.params.activityId);
const activity = ref<Activity>();
const participants = ref<ActivityParticipant[]>([]);
const keywordInput = ref("");
const keyword = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(true);
const participantsLoading = ref(false);
const actionParticipantIds = ref(new Set<number>());
const error = ref("");
const username = localStorage.getItem("active_admin_username") || "超级用户";
let loadSequence = 0;

const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const participantCountLabel = computed(() =>
  keyword.value ? `匹配 ${total.value} 位参与用户` : `共 ${total.value} 位参与用户`,
);
const rangeLabel = computed(() => {
  if (!total.value) return "暂无记录";
  const start = (page.value - 1) * pageSize.value + 1;
  const end = Math.min(page.value * pageSize.value, total.value);
  return `显示第 ${start}-${end} 条`;
});

const applyParticipantPage = (response: ActivityParticipantPage) => {
  participants.value = response.items;
  page.value = response.page;
  pageSize.value = response.page_size;
  total.value = response.total;
};

const participantQuery = () => ({
  keyword: keyword.value || undefined,
  page: page.value,
  pageSize: pageSize.value,
});

const load = async () => {
  loading.value = true;
  error.value = "";
  const sequence = ++loadSequence;
  participantsLoading.value = true;
  try {
    const [currentActivity, currentParticipants] = await Promise.all([
      getActivity(activityId),
      listActivityParticipants(activityId, participantQuery()),
    ]);
    if (sequence !== loadSequence) return;
    activity.value = currentActivity;
    applyParticipantPage(currentParticipants);
  } catch (err) {
    if (sequence === loadSequence) {
      error.value = err instanceof Error ? err.message : "参与者加载失败";
    }
  } finally {
    if (sequence === loadSequence) participantsLoading.value = false;
    loading.value = false;
  }
};

const loadParticipants = async () => {
  const sequence = ++loadSequence;
  participantsLoading.value = true;
  error.value = "";
  try {
    const response = await listActivityParticipants(activityId, participantQuery());
    if (sequence === loadSequence) applyParticipantPage(response);
  } catch (err) {
    if (sequence === loadSequence) {
      error.value = err instanceof Error ? err.message : "参与者加载失败";
    }
  } finally {
    if (sequence === loadSequence) participantsLoading.value = false;
  }
};

const searchParticipants = () => {
  keyword.value = keywordInput.value.trim();
  page.value = 1;
  void loadParticipants();
};

const changePageSize = (size: number) => {
  pageSize.value = size;
  page.value = 1;
  void loadParticipants();
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

.participants-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.participant-search-row {
  display: flex;
  gap: 10px;
  width: min(520px, 100%);
}

.participant-search-row :deep(.el-input) {
  max-width: 420px;
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

.participants-results {
  min-height: 280px;
}

.participants-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #edf1ef;
}

.participants-footer > span {
  color: #849089;
  font-size: 12px;
  white-space: nowrap;
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
  .content-heading,
  .participants-toolbar,
  .participants-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .participant-search-row {
    width: 100%;
  }

  .participant-search-row :deep(.el-input) {
    max-width: none;
  }

  .participants-footer :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .participants-surface {
    padding: 22px 18px;
  }
}
</style>
