<template>
  <section class="mobile-lottery-content">
    <header class="mobile-lottery-header">
      <button class="mobile-lottery-back" type="button" aria-label="返回活动首页" @click="goHome">
        <VanIcon name="arrow-left" />
      </button>
      <div>
        <p class="section-kicker">MOBILE LOTTERY</p>
        <h1>移动端抽奖</h1>
      </div>
      <VanTag class="mobile-lottery-connection" :type="connectionTagType">
        {{ connectionLabel }}
      </VanTag>
    </header>

    <div v-if="loading" class="mobile-lottery-state" aria-live="polite">
      <VanLoading size="24px" color="var(--activity-gold)" />
      <p>正在连接抽奖控制</p>
    </div>

    <div v-else-if="error" class="mobile-lottery-state mobile-lottery-state--error" aria-live="assertive">
      <VanIcon name="warning-o" />
      <p>{{ error }}</p>
      <VanButton plain type="primary" @click="load">重新连接</VanButton>
    </div>

    <template v-else>
      <section class="mobile-lottery-section">
        <div class="mobile-lottery-section-heading">
          <div>
            <p class="section-kicker">PRIZE SELECT</p>
            <h2>选择奖品</h2>
          </div>
          <VanTag :type="activityStatus === 'open' ? 'success' : 'primary'">
            {{ activityStatus === "open" ? "活动进行中" : "暂不可开奖" }}
          </VanTag>
        </div>

        <VanCellGroup v-if="prizes.length" class="mobile-lottery-prize-list">
          <VanCell
            v-for="prize in prizes"
            :key="prize.prize_id"
            clickable
            :class="{ 'mobile-lottery-prize--selected': selectedPrizeId === prize.prize_id }"
            :disabled="!canSelectPrize || selectingPrizeId === prize.prize_id || prize.remaining_quantity <= 0"
            @click="selectPrize(prize.prize_id)"
          >
            <template #icon>
              <div class="mobile-lottery-prize-image">
                <img
                  v-if="mediaURL(prize.image_url)"
                  :src="mediaURL(prize.image_url) || undefined"
                  :alt="prize.name"
                />
                <VanIcon v-else name="gift-o" />
              </div>
            </template>
            <template #title><strong>{{ prize.name }}</strong></template>
            <template #label><span>剩余 {{ prize.remaining_quantity }} 份</span></template>
            <template #value>
              <VanLoading v-if="selectingPrizeId === prize.prize_id" size="16px" />
              <VanIcon v-else-if="selectedPrizeId === prize.prize_id" name="success" />
            </template>
          </VanCell>
        </VanCellGroup>
        <VanEmpty v-else description="暂无可用奖品" />
      </section>

      <p v-if="actionError" class="mobile-lottery-action-error" role="alert">{{ actionError }}</p>

      <section class="mobile-lottery-draw-panel">
        <div class="mobile-lottery-current">
          <span>当前奖品</span>
          <strong>{{ selectedPrize?.name || "请选择奖品" }}</strong>
        </div>
        <p class="mobile-lottery-hint">{{ drawHint }}</p>
        <VanButton
          block
          type="primary"
          class="mobile-lottery-draw-button"
          :loading="phase === 'starting' || phase === 'stopping'"
          :disabled="controlDisabled"
          @click="toggleDraw"
        >
          {{ drawButtonLabel }}
        </VanButton>
      </section>

      <section v-if="lastDraw" class="mobile-lottery-result" aria-live="polite">
        <p class="section-kicker">LATEST RESULT</p>
        <h2>恭喜中奖</h2>
        <p class="mobile-lottery-winner">{{ lastDraw.winner.username }}</p>
        <p class="mobile-lottery-result-meta">
          {{ lastDraw.prize_name }} · 剩余 {{ lastDraw.remaining_quantity }} 份
        </p>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  Button as VanButton,
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Empty as VanEmpty,
  Icon as VanIcon,
  Loading as VanLoading,
  Tag as VanTag,
} from "vant";
import {
  getActivityToken,
  mediaURL,
  mobileLotteryWebSocketURL,
  type Activity,
  type ActivityUserResponse,
  type MobileLotteryAward,
  type MobileLotteryDraw,
  type MobileLotteryPrize,
  type MobileLotteryRound,
  type MobileLotterySnapshot,
} from "../../api/client";
import { activitySessionKey, type ActivitySession } from "./session";

type ConnectionState = "connecting" | "connected" | "offline";
type LotteryPhase = "idle" | "starting" | "rolling" | "stopping";

const props = defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const router = useRouter();
const session = inject<ActivitySession>(activitySessionKey);
const activityId = props.activity.activity_id;
const loading = ref(true);
const error = ref("");
const actionError = ref("");
const connectionState = ref<ConnectionState>("connecting");
const activityStatus = ref<Activity["status"]>(props.activity.status);
const prizes = ref<MobileLotteryPrize[]>([]);
const selectedPrizeId = ref<number>();
const selectingPrizeId = ref<number>();
const lastDraw = ref<MobileLotteryDraw>();
const activeRound = ref<MobileLotteryRound>();
const pendingRoundId = ref<string>();
const phase = ref<LotteryPhase>("idle");
let socket: WebSocket | undefined;
let reconnectTimer: number | undefined;
let reconnectAttempt = 0;
let stopped = false;

const selectedPrize = computed(() => prizes.value.find((prize) => prize.prize_id === selectedPrizeId.value));
const canSelectPrize = computed(() => connectionState.value === "connected" && phase.value === "idle");
const controlDisabled = computed(() => (
  connectionState.value !== "connected"
  || !selectedPrize.value
  || activityStatus.value !== "open"
  || phase.value === "starting"
  || phase.value === "stopping"
  || (phase.value === "idle" && (selectedPrize.value?.remaining_quantity ?? 0) <= 0)
));
const drawButtonLabel = computed(() => ({
  idle: "开始抽奖",
  starting: "准备抽奖",
  rolling: "结束抽奖",
  stopping: "开奖中",
}[phase.value]));
const drawHint = computed(() => {
  if (phase.value === "starting") return "正在通知大屏开始滚动。";
  if (phase.value === "rolling") return "大屏正在滚动，确认后点击结束抽奖。";
  if (phase.value === "stopping") return "大屏已停止滚动，正在揭晓中奖者。";
  if (selectedPrize.value && selectedPrize.value.remaining_quantity <= 0) return "当前奖品库存已用完，请切换其他奖品。";
  if (activityStatus.value !== "open") return "活动开启后才能发起抽奖。";
  return "点击开始后，大屏会同步滚动抽奖。";
});
const connectionLabel = computed(() => ({
  connecting: "连接中",
  connected: "已连接",
  offline: "重连中",
}[connectionState.value]));
const connectionTagType = computed(() => connectionState.value === "connected" ? "success" : "primary");

const goHome = () => router.push({ name: "activity-home", params: { activityId } });
const createRoundId = () => globalThis.crypto?.randomUUID?.()
  || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const send = (payload: Record<string, unknown>) => {
  if (!socket || connectionState.value !== "connected") {
    actionError.value = "抽奖连接尚未就绪，请稍候。";
    return false;
  }
  socket.send(JSON.stringify(payload));
  return true;
};

const flattenPrizes = (awards: MobileLotteryAward[]) => awards
  .flatMap((award) => award.prizes)
  .filter((prize) => prize.is_enabled);

const chooseFallbackPrize = () => {
  if (selectedPrizeId.value && prizes.value.some((prize) => prize.prize_id === selectedPrizeId.value)) return;
  selectedPrizeId.value = prizes.value.find((prize) => prize.remaining_quantity > 0)?.prize_id
    ?? prizes.value[0]?.prize_id;
};

const applySnapshot = (snapshot: MobileLotterySnapshot) => {
  activityStatus.value = snapshot.activity_status;
  prizes.value = flattenPrizes(snapshot.awards);
  const draws = [...snapshot.draws].sort((left, right) => right.draw_id - left.draw_id);
  lastDraw.value = draws[0];
  selectedPrizeId.value = snapshot.selected_prize_id ?? undefined;
  activeRound.value = snapshot.active_round || undefined;
  if (activeRound.value) {
    selectedPrizeId.value = activeRound.value.prize_id;
    pendingRoundId.value = activeRound.value.round_id;
    phase.value = activeRound.value.phase === "stopping" ? "stopping" : "rolling";
  } else {
    pendingRoundId.value = undefined;
    phase.value = "idle";
    chooseFallbackPrize();
  }
};

const applyConfigUpdate = (config: Record<string, unknown>) => {
  const nextPrizes = config.prizes;
  if (!Array.isArray(nextPrizes)) return;
  prizes.value = (nextPrizes as MobileLotteryPrize[]).filter((prize) => prize.is_enabled);
  chooseFallbackPrize();
};

const updateDraw = (draw: MobileLotteryDraw) => {
  const prize = prizes.value.find((item) => item.prize_id === draw.prize_id);
  if (prize) prize.remaining_quantity = draw.remaining_quantity;
  lastDraw.value = draw;
  activeRound.value = undefined;
  pendingRoundId.value = undefined;
  phase.value = "idle";
};

const handleMessage = (event: MessageEvent<string>) => {
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(event.data) as Record<string, unknown>;
  } catch {
    return;
  }
  if (payload.type === "lottery.ready") {
    applySnapshot(payload as unknown as MobileLotterySnapshot);
    loading.value = false;
    error.value = "";
    actionError.value = "";
    connectionState.value = "connected";
    reconnectAttempt = 0;
    return;
  }
  if (payload.type === "lottery.prize.selected") {
    const prizeId = payload.selected_prize_id;
    if (typeof prizeId === "number" && Number.isInteger(prizeId) && prizeId > 0) {
      selectedPrizeId.value = prizeId;
      selectingPrizeId.value = undefined;
    }
    return;
  }
  if (payload.type === "lottery.draw.started" && payload.round) {
    const round = payload.round as MobileLotteryRound;
    activeRound.value = round;
    pendingRoundId.value = round.round_id;
    selectedPrizeId.value = round.prize_id;
    phase.value = round.phase === "stopping" ? "stopping" : "rolling";
    actionError.value = "";
    return;
  }
  if (payload.type === "lottery.draw.stopping") {
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if (roundId && (roundId === pendingRoundId.value || roundId === activeRound.value?.round_id)) {
      phase.value = "stopping";
      if (activeRound.value?.round_id === roundId) activeRound.value = { ...activeRound.value, phase: "stopping" };
    }
    return;
  }
  if (payload.type === "lottery.drawn" && payload.draw) {
    updateDraw(payload.draw as MobileLotteryDraw);
    actionError.value = "";
    return;
  }
  if (payload.type === "lottery.config.updated" && payload.config) {
    applyConfigUpdate(payload.config as Record<string, unknown>);
    return;
  }
  if (payload.type === "lottery.reset" && payload.snapshot) {
    applySnapshot(payload.snapshot as MobileLotterySnapshot);
    lastDraw.value = undefined;
    actionError.value = "";
    return;
  }
  if (payload.type === "lottery.draw.error") {
    selectingPrizeId.value = undefined;
    actionError.value = String(payload.detail || "抽奖失败");
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if (!roundId || roundId === pendingRoundId.value || roundId === activeRound.value?.round_id) {
      activeRound.value = undefined;
      pendingRoundId.value = undefined;
      phase.value = "idle";
    }
    if (payload.code === "unauthorized" && loading.value) {
      stopped = true;
      error.value = actionError.value;
      loading.value = false;
    }
  }
};

const scheduleReconnect = () => {
  if (stopped || reconnectTimer !== undefined) return;
  reconnectAttempt += 1;
  const delay = Math.min(8000, 500 * 2 ** Math.min(reconnectAttempt - 1, 4));
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = undefined;
    connect();
  }, delay);
};

function connect() {
  if (stopped) return;
  const token = getActivityToken(activityId);
  if (!token) {
    session?.logout();
    return;
  }
  connectionState.value = "connecting";
  const current = new WebSocket(mobileLotteryWebSocketURL(activityId));
  socket = current;
  current.onopen = () => current.send(JSON.stringify({ type: "auth", token }));
  current.onmessage = handleMessage;
  current.onerror = () => current.close();
  current.onclose = () => {
    if (socket !== current) return;
    socket = undefined;
    if (!stopped) {
      connectionState.value = "offline";
      scheduleReconnect();
    }
  };
}

const load = () => {
  stopped = false;
  error.value = "";
  actionError.value = "";
  loading.value = true;
  if (socket) socket.close();
  connect();
};

const selectPrize = (prizeId: number) => {
  if (!canSelectPrize.value || selectingPrizeId.value === prizeId) return;
  const prize = prizes.value.find((item) => item.prize_id === prizeId);
  if (!prize || prize.remaining_quantity <= 0 || selectedPrizeId.value === prizeId) return;
  selectingPrizeId.value = prizeId;
  actionError.value = "";
  if (!send({ type: "lottery.prize.select", prize_id: prizeId })) selectingPrizeId.value = undefined;
};

const toggleDraw = () => {
  if (phase.value === "rolling" && activeRound.value) {
    if (send({
      type: "lottery.draw.stop",
      prize_id: activeRound.value.prize_id,
      round_id: activeRound.value.round_id,
    })) phase.value = "stopping";
    return;
  }
  if (phase.value !== "idle" || !selectedPrize.value || selectedPrize.value.remaining_quantity <= 0) return;
  const roundId = createRoundId();
  if (send({ type: "lottery.draw.start", prize_id: selectedPrize.value.prize_id, round_id: roundId })) {
    pendingRoundId.value = roundId;
    phase.value = "starting";
    actionError.value = "";
  }
};

onMounted(connect);
onBeforeUnmount(() => {
  stopped = true;
  if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
  socket?.close();
  socket = undefined;
});
</script>

<style scoped>
.mobile-lottery-content {
  box-sizing: border-box;
  min-height: calc(100dvh - env(safe-area-inset-top));
  padding: 20px 16px calc(88px + env(safe-area-inset-bottom));
}

.mobile-lottery-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.mobile-lottery-header h1,
.mobile-lottery-section h2,
.mobile-lottery-result h2 {
  margin: 0;
}

.mobile-lottery-header h1 {
  margin-top: 4px;
  color: var(--activity-text);
  font-size: 24px;
  line-height: 1.3;
}

.mobile-lottery-back {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  flex: 0 0 auto;
  border: 1px solid var(--activity-line);
  border-radius: 10px;
  color: var(--activity-text-soft);
  background: var(--activity-surface);
  font-size: 19px;
}

.mobile-lottery-connection {
  margin-left: auto;
  flex: 0 0 auto;
}

.mobile-lottery-section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  margin: 0 4px 12px;
}

.mobile-lottery-section h2,
.mobile-lottery-result h2 {
  margin-top: 5px;
  color: var(--activity-text);
  font-size: 20px;
  line-height: 1.35;
}

.mobile-lottery-prize-list {
  overflow: hidden;
  border: 1px solid var(--activity-line);
  border-radius: 13px;
  background: var(--activity-surface);
}

.mobile-lottery-prize-list :deep(.van-cell) {
  min-height: 76px;
  color: var(--activity-text);
  background: var(--activity-surface);
}

.mobile-lottery-prize-list :deep(.van-cell::after) { border-color: var(--activity-line); }
.mobile-lottery-prize-list :deep(.van-cell__left-icon) { display: flex; align-items: center; margin-right: 12px; }
.mobile-lottery-prize-list :deep(.van-cell__title) { color: var(--activity-text); font-size: 15px; }
.mobile-lottery-prize-list :deep(.van-cell__label) { margin-top: 5px; color: var(--activity-text-muted); }
.mobile-lottery-prize-list :deep(.van-cell__value) {
  display: flex;
  align-items: center;
  color: var(--activity-gold-strong);
}
.mobile-lottery-prize--selected { background: rgb(213 179 107 / 10%) !important; }

.mobile-lottery-prize-image {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgb(213 179 107 / 30%);
  border-radius: 10px;
  color: var(--activity-gold-strong);
  background: var(--activity-surface-strong);
  font-size: 22px;
}

.mobile-lottery-prize-image img { width: 100%; height: 100%; object-fit: cover; }

.mobile-lottery-action-error {
  margin: 16px 4px 0;
  color: var(--activity-danger);
  font-size: 13px;
  line-height: 1.5;
}

.mobile-lottery-draw-panel,
.mobile-lottery-result {
  margin-top: 22px;
  padding: 18px;
  border: 1px solid var(--activity-line);
  border-radius: 13px;
  background: var(--activity-surface);
}

.mobile-lottery-current { display: grid; gap: 5px; }
.mobile-lottery-current span,
.mobile-lottery-hint,
.mobile-lottery-result-meta { color: var(--activity-text-muted); font-size: 12px; line-height: 1.5; }
.mobile-lottery-current strong {
  color: var(--activity-gold-strong);
  font-size: 18px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.mobile-lottery-hint { min-height: 18px; margin: 12px 0 0; }

.mobile-lottery-draw-button {
  height: 48px;
  margin-top: 16px;
  border-radius: 10px;
  font-weight: 700;
}

.mobile-lottery-result { border-color: rgb(213 179 107 / 48%); text-align: center; }
.mobile-lottery-result h2 { color: var(--activity-gold-strong); }
.mobile-lottery-winner {
  margin: 14px 0 3px;
  color: var(--activity-text);
  font-size: 26px;
  font-weight: 750;
  overflow-wrap: anywhere;
}
.mobile-lottery-result-meta { margin: 0; }

.mobile-lottery-state {
  display: grid;
  min-height: 360px;
  place-items: center;
  align-content: center;
  gap: 14px;
  color: var(--activity-text-muted);
  text-align: center;
}

.mobile-lottery-state p { margin: 0; }
.mobile-lottery-state--error .van-icon { color: var(--activity-danger); font-size: 28px; }
.mobile-lottery-state--error .van-button { min-width: 120px; }

@media (min-width: 601px) {
  .mobile-lottery-content { max-width: 600px; margin: 0 auto; }
}
</style>
