<template>
  <div class="activity-management">
    <ActivitySidebar
      :activity="activity"
      :activity-id="activityId"
      active="lottery"
      :username="username"
    />

    <section class="workspace">
      <header class="workspace-topbar">
        <div class="breadcrumb">
          <span>活动管理</span><b>/</b><span>实时抽奖</span><b>/</b>
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
        <el-alert v-if="error" :title="error" type="error" show-icon class="page-alert" />
        <el-skeleton v-if="loading" :rows="10" animated />

        <template v-else-if="activity && config">
          <section class="activity-titlebar">
            <div>
              <p class="eyebrow">LIVE LOTTERY</p>
              <h1>实时抽奖</h1>
              <p class="activity-meta">{{ activity.name }} · 开奖与大屏展示通过 WebSocket 实时同步</p>
            </div>
            <span class="status-badge" :class="`status-badge--${activity.status}`">
              <i aria-hidden="true"></i>{{ statusLabel(activity.status) }}
            </span>
          </section>

          <section class="lottery-grid">
            <article class="content-surface config-card">
              <header class="content-heading">
                <div><p class="eyebrow">LOTTERY SETTINGS</p><h2>奖项与奖品</h2></div>
                <span class="content-hint">配置和历史使用 HTTP 保存</span>
              </header>

              <el-form label-position="top" class="lottery-form" @submit.prevent="saveConfig">
                <div class="rule-grid">
                  <el-form-item label="跨奖品不重复中奖">
                    <el-switch v-model="form.no_repeat_across_prizes" active-text="启用" inactive-text="关闭" />
                  </el-form-item>
                  <el-form-item label="滚动候选人数">
                    <el-input-number
                      v-model="form.rolling_name_count"
                      :min="1"
                      :max="20"
                      :step="1"
                      controls-position="right"
                    />
                  </el-form-item>
                </div>

                <section class="editor-section prize-tree-section">
                  <div class="editor-heading">
                    <h3>奖项与奖品</h3>
                    <span>{{ form.awards.length }} 个奖项 · {{ form.prizes.length }} 个奖品</span>
                  </div>
                  <div v-if="!form.awards.length" class="tree-empty">
                    <p>先创建奖项，再在奖项下面添加奖品。</p>
                    <el-button plain @click="addAward">+ 添加奖项</el-button>
                  </div>
                  <div v-else class="award-tree">
                    <article
                      v-for="(award, index) in form.awards"
                      :key="award.award_id ?? `award-${index}`"
                      class="award-node"
                    >
                      <header class="award-node-header">
                        <div class="award-node-name">
                          <span class="tree-node-mark" aria-hidden="true">◆</span>
                          <el-input v-model="award.name" placeholder="例如：三等奖" maxlength="100" />
                        </div>
                        <div class="award-sort">
                          <span>排序</span>
                          <el-input-number
                            v-model="award.sort_order"
                            aria-label="奖项排序"
                            :min="0"
                            :max="999"
                            controls-position="right"
                          />
                        </div>
                        <div class="award-node-actions">
                          <el-tag v-if="!isAwardSaved(award)" type="warning" size="small">待保存</el-tag>
                          <el-button text type="danger" @click="removeAward(index)">删除奖项</el-button>
                        </div>
                      </header>
                      <div class="award-node-children">
                        <div v-if="!prizesForAward(award).length" class="tree-empty-child">
                          还没有奖品，请从这里添加
                        </div>
                        <div
                          v-for="(prize, prizeIndex) in prizesForAward(award)"
                          :key="prize.prize_id ?? `prize-${award.award_id}-${prizeIndex}`"
                          class="prize-row"
                        >
                           <div class="prize-node-name">
                             <span class="tree-connector" aria-hidden="true">└</span>
                             <div class="prize-name-fields">
                               <el-input v-model="prize.name" placeholder="例如：无线耳机" maxlength="200" />
                               <PrizeImageEditor :prize="prize" />
                             </div>
                           </div>
                          <el-input-number
                            v-model="prize.quantity"
                            aria-label="奖品数量"
                            :min="1"
                            :max="100000"
                            controls-position="right"
                          />
                          <el-switch v-model="prize.is_enabled" active-text="启用" />
                          <el-button text type="danger" @click="removePrize(prize)">删除奖品</el-button>
                        </div>
                        <el-button
                          plain
                          size="small"
                          :disabled="award.award_id === null"
                          @click="addPrize(award)"
                        >+ 添加奖品</el-button>
                        <p v-if="!isAwardSaved(award)" class="editor-note">奖品会随本次配置一起保存。</p>
                      </div>
                    </article>
                    <el-button plain @click="addAward">+ 添加奖项</el-button>
                  </div>
                  <p class="editor-note">奖项排序值越小越靠前；奖品数量不能调低到已经产生的中奖记录以下。</p>
                </section>

                <section class="editor-section entry-section">
                  <div class="editor-heading">
                    <h3>抽奖名单</h3><span>{{ form.entry_summary.total }} 位参与者</span>
                  </div>
                  <div class="entry-summary">
                    <div class="entry-summary-stats">
                      <span><strong>{{ form.entry_summary.total }}</strong>总人数</span>
                      <span><strong>{{ form.entry_summary.eligible }}</strong>可抽奖</span>
                      <span><strong>{{ form.entry_summary.blacklisted }}</strong>黑名单</span>
                      <span><strong>{{ form.entry_summary.whitelisted }}</strong>白名单</span>
                      <span><strong>{{ form.entry_summary.inactive }}</strong>已停用</span>
                    </div>
                    <el-button type="primary" plain @click="entryDialogVisible = true">
                      配置黑白名单
                    </el-button>
                  </div>
                  <p class="editor-note">存在白名单时只抽取白名单用户；黑名单优先排除，停用用户始终不能中奖。</p>
                </section>

                <div class="form-actions">
                  <el-button native-type="submit" type="primary" :loading="saving">保存抽奖配置</el-button>
                </div>
              </el-form>
            </article>

            <aside class="content-surface control-card">
              <header class="content-heading">
                <div><p class="eyebrow">CONTROL CENTER</p><h2>开奖控制</h2></div>
                <span class="connection-dot" :class="{ 'connection-dot--online': connected }">
                  {{ connected ? "已连接" : "重连中" }}
                </span>
              </header>
              <el-alert
                v-if="!connected"
                title="实时连接未就绪，开奖按钮已禁用"
                type="warning"
                :closable="false"
                show-icon
              />
              <div class="control-block">
                <label for="prize-select">选择要抽取的奖品</label>
                <el-select id="prize-select" v-model="selectedPrizeId" class="prize-select" placeholder="请选择奖品">
                  <el-option
                    v-for="prize in savedPrizes"
                    :key="prize.prize_id ?? prize.name"
                    :label="`${prize.name}（剩余 ${prize.remaining_quantity}）`"
                    :value="prize.prize_id"
                    :disabled="!prize.is_enabled || prize.remaining_quantity <= 0"
                  />
                </el-select>
              </div>
              <button
                class="draw-button"
                type="button"
                :disabled="
                  !connected || !selectedPrizeId || drawBusy || activity.status !== 'open'
                "
                @click="drawOne"
              >
                <span class="draw-button-mark">✦</span>
                <span>{{ drawBusy ? "开奖处理中" : "抽取 1 人" }}</span>
              </button>
              <button
                class="reset-button"
                type="button"
                :disabled="!connected || drawBusy"
                @click="resetLottery"
              >
                重置全部中奖记录
              </button>
              <p class="control-note">开奖成功后，管理端获得完整中奖者信息，大屏只接收用户名和中奖状态。</p>
              <div v-if="latestDraw" class="latest-draw">
                <span class="latest-label">最近一次中奖</span>
                <strong>{{ latestDraw.winner.username }}</strong>
                <span>
                  {{ latestDraw.award_name }} · {{ latestDraw.prize_name }} · 第 {{ latestDraw.draw_number }} 人
                </span>
              </div>
            </aside>
          </section>

          <section class="content-surface history-card">
            <header class="content-heading">
              <div><p class="eyebrow">WINNER HISTORY</p><h2>中奖记录</h2></div>
              <span class="content-hint">共 {{ history.length }} 条 · 实时更新</span>
            </header>
            <el-empty v-if="!history.length" description="还没有中奖记录" />
            <el-table v-else :data="history" stripe class="history-table">
              <el-table-column prop="draw_id" label="编号" width="90" />
              <el-table-column label="奖项 / 奖品" min-width="180">
                <template #default="{ row }">{{ row.award_name }} / {{ row.prize_name }}</template>
              </el-table-column>
              <el-table-column label="中奖者" min-width="150">
                <template #default="{ row }">
                  <strong>{{ row.winner.username }}</strong><small>{{ row.winner.phone }}</small>
                </template>
              </el-table-column>
              <el-table-column label="序号" width="90">
                <template #default="{ row }">第 {{ row.draw_number }} 人</template>
              </el-table-column>
              <el-table-column label="剩余库存" width="110" prop="remaining_quantity" />
              <el-table-column label="时间" min-width="180">
                <template #default="{ row }">{{ formatDate(row.drawn_at) }}</template>
              </el-table-column>
            </el-table>
          </section>

          <LotteryEntriesDialog
            v-model="entryDialogVisible"
            :activity-id="activityId"
            :summary="form.entry_summary"
            @summary-updated="updateEntrySummary"
          />
        </template>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRoute } from "vue-router";
import ActivitySidebar from "../../components/ActivitySidebar.vue";
import {
  getActivity,
  getLottery,
  getLotteryHistory,
  type Activity,
  type LotteryConfig,
  type LotteryDraw,
  type LotteryEntrySummary,
  type LotterySnapshot,
} from "../../api/client";
import LotteryEntriesDialog from "./LotteryEntriesDialog.vue";
import PrizeImageEditor from "./PrizeImageEditor.vue";
import {
  collectPrizeImageActions,
  refreshLotteryAfterImages,
  syncPrizeImages,
} from "./lottery-image-actions";
import {
  saveLotteryConfig,
  type FormAward,
  type FormPrize,
  type LotteryForm,
} from "./lottery-config-form";
import { useLotterySocket } from "./useLotterySocket";
const route = useRoute();
const activityId = String(route.params.activityId);
const username = localStorage.getItem("active_admin_username") || "超级用户";
const activity = ref<Activity>();
const config = ref<LotteryConfig>();
const history = ref<LotteryDraw[]>([]);
const loading = ref(true);
const saving = ref(false);
const drawBusy = ref(false);
const error = ref("");
const selectedPrizeId = ref<number>();
const entryDialogVisible = ref(false);
let nextTemporaryAwardId = -1;
let configRefreshVersion = 0;
const form = reactive<LotteryForm>({
  activity_id: activityId,
  no_repeat_across_prizes: true,
  rolling_name_count: 8,
  awards: [],
  prizes: [],
  entry_summary: {
    total: 0,
    eligible: 0,
    blacklisted: 0,
    whitelisted: 0,
    inactive: 0,
  },
  updated_at: "",
});
const savedPrizes = computed(() => form.prizes.filter((prize) => Boolean(prize.prize_id)));
const latestDraw = computed(() => history.value[0]);
const isAwardSaved = (award: FormAward) => typeof award.award_id === "number" && award.award_id > 0;
const statusLabel = (status: Activity["status"]) =>
  ({ closed: "已关闭", open: "进行中", ended: "已结束" })[status];
const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
const applyConfig = (response: LotteryConfig) => {
  config.value = response;
  form.activity_id = response.activity_id;
  form.no_repeat_across_prizes = response.no_repeat_across_prizes;
  form.rolling_name_count = response.rolling_name_count;
  form.awards = response.awards.map((award) => ({ ...award }));
  form.prizes = response.prizes.map((prize) => ({ ...prize }));
  form.entry_summary = { ...response.entry_summary };
  form.updated_at = response.updated_at;
  if (!selectedPrizeId.value || !form.prizes.some((prize) => prize.prize_id === selectedPrizeId.value)) {
    selectedPrizeId.value = form.prizes.find(
      (prize) => prize.is_enabled && prize.remaining_quantity > 0,
    )?.prize_id ?? undefined;
  }
};
const upsertHistory = (draw: LotteryDraw) => {
  const index = history.value.findIndex((item) => item.draw_id === draw.draw_id);
  if (index >= 0) history.value[index] = draw;
  else history.value.unshift(draw);
  const prize = form.prizes.find((item) => item.prize_id === draw.prize_id);
  if (prize) prize.remaining_quantity = draw.remaining_quantity;
};
const applySnapshot = (snapshot: LotterySnapshot) => {
  if (activity.value) activity.value.status = snapshot.activity_status;
  history.value = [...snapshot.draws].sort((left, right) => right.draw_id - left.draw_id);
  for (const award of snapshot.awards) {
    for (const prize of award.prizes) {
      const target = form.prizes.find((item) => item.prize_id === prize.prize_id);
      if (target) target.remaining_quantity = prize.remaining_quantity;
    }
  }
};
const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const [currentActivity, currentConfig, currentHistory] = await Promise.all([
      getActivity(activityId),
      getLottery(activityId),
      getLotteryHistory(activityId),
    ]);
    activity.value = currentActivity;
    applyConfig(currentConfig);
    history.value = currentHistory.items;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "抽奖页面加载失败";
  } finally {
    loading.value = false;
  }
};
const saveConfig = async () => {
  saving.value = true;
  configRefreshVersion += 1;
  const imageActions = collectPrizeImageActions(form.prizes);
  try {
    applyConfig(await saveLotteryConfig(activityId, form));
    const imageFailed = await syncPrizeImages(activityId, form.prizes, imageActions);
    if (!imageFailed && imageActions.length) await refreshLotteryAfterImages(activityId, applyConfig);
    if (imageFailed) ElMessage.warning("抽奖配置已保存，但部分奖品图片保存失败");
    else ElMessage.success("抽奖配置已保存并同步大屏");
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "保存失败，请稍后重试");
  } finally {
    saving.value = false;
  }
};
const addAward = () => {
  form.awards.push({
    award_id: nextTemporaryAwardId--,
    name: "新奖项",
    sort_order: form.awards.length,
  });
};
const removeAward = (index: number) => {
  const award = form.awards[index];
  if (award && award.award_id !== null) {
    form.prizes = form.prizes.filter((prize) => prize.award_id !== award.award_id);
  }
  form.awards.splice(index, 1);
};
const prizesForAward = (award: FormAward) => {
  if (award.award_id === null) return [];
  return form.prizes.filter((prize) => prize.award_id === award.award_id);
};
const addPrize = (award: FormAward) => {
  if (award.award_id === null) {
    ElMessage.warning("请先添加奖项");
    return;
  }
  const sortOrder = prizesForAward(award).length;
  form.prizes.push({
    prize_id: null,
    award_id: award.award_id,
    name: "新奖品",
    quantity: 1,
    remaining_quantity: 1,
    sort_order: sortOrder,
    is_enabled: true,
    image_url: null,
  });
};
const removePrize = (prize: FormPrize) => {
  const index = form.prizes.indexOf(prize);
  if (index >= 0) form.prizes.splice(index, 1);
};
const updateEntrySummary = (summary: LotteryEntrySummary) => {
  form.entry_summary = { ...summary };
  if (config.value) config.value.entry_summary = { ...summary };
};
const drawOne = () => {
  if (!selectedPrizeId.value) return;
  const requestId = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  if (!send({
    type: "lottery.draw.request",
    prize_id: selectedPrizeId.value,
    request_id: requestId,
  })) return;
  drawBusy.value = true;
};
const resetLottery = async () => {
  try {
    await ElMessageBox.confirm(
      "重置后所有中奖记录会清空，且大屏会同步清除中奖名单。",
      "确认重置抽奖",
      {
        confirmButtonText: "确认重置",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }
  if (!send({ type: "lottery.reset.request" })) return;
  drawBusy.value = true;
};
const handleMessage = (event: MessageEvent<string>) => {
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(event.data) as Record<string, unknown>;
  } catch {
    return;
  }
  if (payload.type === "lottery.ready") {
    connected.value = true;
    applySnapshot(payload as unknown as LotterySnapshot);
    drawBusy.value = false;
  } else if (payload.type === "lottery.draw.result" && payload.draw) {
    upsertHistory(payload.draw as LotteryDraw);
    drawBusy.value = false;
  } else if (payload.type === "lottery.draw.error") {
    drawBusy.value = false;
    ElMessage.error(String(payload.detail || "开奖失败"));
    if (payload.code === "unauthorized") {
      window.dispatchEvent(new CustomEvent("admin-unauthorized"));
    }
  } else if (payload.type === "lottery.reset" && payload.snapshot) {
    applySnapshot(payload.snapshot as LotterySnapshot);
    drawBusy.value = false;
    ElMessage.success("中奖记录已重置");
  } else if (payload.type === "lottery.config.updated") {
    if (saving.value) return;
    const refreshVersion = configRefreshVersion;
    void getLottery(activityId).then((latest) => {
      if (!saving.value && refreshVersion === configRefreshVersion) applyConfig(latest);
    }).catch(() => undefined);
  }
};
const { connected, send } = useLotterySocket(activityId, handleMessage);
onMounted(() => {
  void load();
});
</script>

<style scoped src="./lottery.css"></style>
