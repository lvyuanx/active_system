<template>
  <el-dialog
    :model-value="modelValue"
    class="lottery-entry-dialog"
    width="calc(100vw - 32px)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="entry-dialog-heading">
        <div>
          <p class="eyebrow">LOTTERY ELIGIBILITY</p>
          <h2>配置抽奖名单</h2>
          <p>按需搜索参与者，黑名单和白名单切换后立即生效。</p>
        </div>
        <span class="entry-dialog-count">共 {{ summary.total }} 人</span>
      </div>
    </template>

    <div class="entry-dialog-toolbar">
      <div class="entry-search-row">
        <el-input
          v-model="keywordInput"
          clearable
          placeholder="搜索用户名或手机号"
          @keyup.enter="searchEntries"
          @clear="searchEntries"
        />
        <el-button type="primary" :loading="loading" @click="searchEntries">搜索</el-button>
      </div>
      <el-radio-group v-model="statusFilter" class="entry-status-filter" @change="changeStatus">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="eligible">可抽奖</el-radio-button>
        <el-radio-button value="blacklisted">黑名单</el-radio-button>
        <el-radio-button value="whitelisted">白名单</el-radio-button>
        <el-radio-button value="inactive">已停用</el-radio-button>
      </el-radio-group>
    </div>

    <p class="entry-dialog-note">黑白名单互斥；停用用户即使被加入白名单，也不会参与开奖。</p>

    <el-table
      v-loading="loading"
      :data="entries"
      row-key="activity_user_id"
      class="entry-dialog-table"
      max-height="52vh"
    >
      <el-table-column label="参与者" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="entry-person">
            <strong>{{ row.username }}</strong>
            <small>{{ row.phone }}</small>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="150">
        <template #default="{ row }">
          <div class="entry-status-stack">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain">
              {{ row.is_active ? "可用" : "已停用" }}
            </el-tag>
            <el-tag v-if="row.is_blacklisted" type="danger" size="small" effect="plain">
              黑名单
            </el-tag>
            <el-tag v-if="row.is_whitelisted" type="warning" size="small" effect="plain">
              白名单
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="黑名单" width="105" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_blacklisted"
            :loading="isUpdating(row.activity_user_id)"
            :disabled="isUpdating(row.activity_user_id)"
            @change="updateFlag(row, 'blacklisted', Boolean($event))"
          />
        </template>
      </el-table-column>
      <el-table-column label="白名单" width="105" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_whitelisted"
            :loading="isUpdating(row.activity_user_id)"
            :disabled="isUpdating(row.activity_user_id)"
            @change="updateFlag(row, 'whitelisted', Boolean($event))"
          />
        </template>
      </el-table-column>
      <template #empty>
        <el-empty
          :description="keywordInput || statusFilter !== 'all' ? '当前筛选下没有参与者' : '还没有参与者'"
          :image-size="54"
        />
      </template>
    </el-table>

    <template #footer>
      <div class="entry-dialog-footer">
        <span>{{ rangeLabel }}</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[20, 50, 100]"
          :total="total"
          @current-change="loadEntries"
          @size-change="changePageSize"
        />
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  getLotteryEntries,
  updateLotteryEntry,
  type LotteryEntry,
  type LotteryEntryStatus,
  type LotteryEntrySummary,
} from "../../api/client";

const props = defineProps<{
  modelValue: boolean;
  activityId: string;
  summary: LotteryEntrySummary;
}>();
const emit = defineEmits<{
  (event: "update:modelValue", value: boolean): void;
  (event: "summary-updated", value: LotteryEntrySummary): void;
}>();

const entries = ref<LotteryEntry[]>([]);
const keywordInput = ref("");
const statusFilter = ref<LotteryEntryStatus>("all");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const updatingIds = ref(new Set<number>());
let loadSequence = 0;

const rangeLabel = computed(() => {
  if (!total.value) return "暂无记录";
  const start = (page.value - 1) * pageSize.value + 1;
  const end = Math.min(page.value * pageSize.value, total.value);
  return `显示第 ${start}-${end} 条`;
});

const isUpdating = (activityUserId: number) => updatingIds.value.has(activityUserId);

const loadEntries = async () => {
  const sequence = ++loadSequence;
  loading.value = true;
  try {
    const response = await getLotteryEntries(props.activityId, {
      keyword: keywordInput.value.trim() || undefined,
      status: statusFilter.value,
      page: page.value,
      pageSize: pageSize.value,
    });
    if (sequence !== loadSequence || !props.modelValue) return;
    entries.value = response.items;
    page.value = response.page;
    pageSize.value = response.page_size;
    total.value = response.total;
    emit("summary-updated", response.summary);
  } catch (error) {
    if (sequence === loadSequence) {
      ElMessage.error(error instanceof Error ? error.message : "名单加载失败，请稍后重试");
    }
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
};

const refreshCurrentPage = async () => {
  await loadEntries();
  if (props.modelValue && !entries.value.length && page.value > 1) {
    page.value -= 1;
    await loadEntries();
  }
};

const openDialog = () => {
  keywordInput.value = "";
  statusFilter.value = "all";
  page.value = 1;
  total.value = 0;
  entries.value = [];
  void loadEntries();
};

const searchEntries = () => {
  page.value = 1;
  void loadEntries();
};

const changeStatus = () => {
  page.value = 1;
  void loadEntries();
};

const changePageSize = (size: number) => {
  pageSize.value = size;
  page.value = 1;
  void loadEntries();
};

const updateFlag = async (
  entry: LotteryEntry,
  flag: "blacklisted" | "whitelisted",
  enabled: boolean,
) => {
  if (isUpdating(entry.activity_user_id)) return;
  const pending = new Set(updatingIds.value);
  pending.add(entry.activity_user_id);
  updatingIds.value = pending;
  const payload = {
    is_blacklisted: flag === "blacklisted" ? enabled : entry.is_blacklisted,
    is_whitelisted: flag === "whitelisted" ? enabled : entry.is_whitelisted,
  };
  if (flag === "blacklisted" && enabled) payload.is_whitelisted = false;
  if (flag === "whitelisted" && enabled) payload.is_blacklisted = false;
  try {
    const response = await updateLotteryEntry(props.activityId, entry.activity_user_id, payload);
    emit("summary-updated", response.summary);
    await refreshCurrentPage();
    ElMessage.success("名单规则已更新");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "保存失败，请稍后重试");
  } finally {
    const next = new Set(updatingIds.value);
    next.delete(entry.activity_user_id);
    updatingIds.value = next;
  }
};

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) openDialog();
    else loadSequence += 1;
  },
);
</script>

<style scoped>
.entry-dialog-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.entry-dialog-heading h2,
.entry-dialog-heading p {
  margin: 0;
}

.entry-dialog-heading h2 {
  color: #26332f;
  font-size: 20px;
}

.entry-dialog-heading p:last-child {
  margin-top: 6px;
  color: #849089;
  font-size: 12px;
  font-weight: 400;
}

.entry-dialog-count {
  flex: none;
  padding: 6px 10px;
  color: #0f6652;
  background: #e4f3ee;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 700;
}

.entry-dialog-toolbar {
  display: grid;
  gap: 14px;
  margin-bottom: 10px;
}

.entry-search-row {
  display: flex;
  gap: 10px;
}

.entry-search-row :deep(.el-input) {
  max-width: 420px;
}

.entry-status-filter {
  max-width: 100%;
  overflow-x: auto;
}

.entry-dialog-note {
  margin: 0 0 12px;
  color: #849089;
  font-size: 12px;
}

.entry-dialog-table :deep(.el-table__cell) {
  padding: 10px 0;
}

.entry-dialog-table :deep(.el-table__body-wrapper) {
  max-height: min(420px, calc(100vh - 330px)) !important;
}

.entry-person {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entry-person strong {
  color: #26332f;
  font-size: 14px;
}

.entry-person small {
  color: #849089;
  font-size: 11px;
}

.entry-status-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.entry-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.entry-dialog-footer > span {
  color: #849089;
  font-size: 12px;
}

@media (max-width: 720px) {
  .entry-dialog-heading {
    flex-direction: column;
    gap: 10px;
  }

  .entry-search-row {
    flex-direction: column;
  }

  .entry-search-row :deep(.el-input) {
    max-width: none;
  }

  .entry-status-filter {
    display: flex;
    width: max-content;
  }

  .entry-dialog-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .entry-dialog-footer :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

:global(.lottery-entry-dialog) {
  margin: 16px auto !important;
  max-height: calc(100vh - 32px);
  max-width: 960px;
}

:global(.lottery-entry-dialog .el-dialog__body) {
  padding-top: 4px;
}
</style>
