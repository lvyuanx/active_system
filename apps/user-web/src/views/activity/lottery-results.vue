<template>
  <section class="lottery-results-content">
    <header class="lottery-results-header">
      <button class="lottery-results-back" type="button" aria-label="返回活动首页" @click="goHome">
        <VanIcon name="arrow-left" />
      </button>
      <div>
        <p class="section-kicker">PRIZE ACTIVITY</p>
        <h1>抽奖活动</h1>
      </div>
      <VanTag class="lottery-results-connection" :type="connectionTagType">
        {{ connectionLabel }}
      </VanTag>
    </header>

    <div v-if="loading" class="lottery-results-state" aria-live="polite">
      <VanLoading size="24px" color="var(--activity-gold)" />
      <p>正在加载抽奖活动</p>
    </div>

    <div v-else-if="error" class="lottery-results-state lottery-results-state--error" aria-live="assertive">
      <VanIcon name="warning-o" />
      <p>{{ error }}</p>
      <VanButton plain type="primary" @click="load">重新连接</VanButton>
    </div>

    <template v-else>
      <section class="lottery-results-section">
        <div class="lottery-results-section-heading">
          <div>
            <p class="section-kicker">PRIZE BOARD</p>
            <h2>奖品展示</h2>
          </div>
          <VanTag :type="activityTagType">{{ activityStatusLabel }}</VanTag>
        </div>

        <VanSwipe
          v-if="prizes.length"
          v-model:current="activeIndex"
          class="lottery-results-swipe"
          :loop="prizes.length > 1"
          indicator-color="var(--activity-gold-strong)"
          @change="handleSlideChange"
        >
          <VanSwipeItem v-for="(prize, index) in prizes" :key="prize.prize_id">
            <article class="lottery-results-slide">
              <div class="lottery-results-prize-image">
                <img
                  v-if="prizeImageURL(prize) && canShowImage(prize.image_url)"
                  :src="prizeImageURL(prize) || undefined"
                  :alt="prize.name"
                  @error="markImageFailed(prize.image_url)"
                />
                <VanIcon v-else name="gift-o" />
              </div>
              <div class="lottery-results-slide-copy">
                <p>{{ prize.award_name }}</p>
                <h3>{{ prize.name }}</h3>
                <span>{{ index + 1 }} / {{ prizes.length }}</span>
              </div>
            </article>
          </VanSwipeItem>
        </VanSwipe>
        <VanEmpty v-else description="暂无启用奖品" />
      </section>

      <section v-if="currentPrize" class="lottery-results-info" aria-live="polite">
        <div class="lottery-results-info-heading">
          <div>
            <p class="section-kicker">PRIZE INFO</p>
            <h2>{{ currentPrize.name }}</h2>
          </div>
          <VanTag :type="currentPrizeTagType">{{ currentPrizeStatusLabel }}</VanTag>
        </div>
        <p class="lottery-results-award">{{ currentPrize.award_name }}</p>
        <div class="lottery-results-stats">
          <span>总数 {{ currentPrize.quantity }} 份</span>
          <span>剩余 {{ currentPrize.remaining_quantity }} 份</span>
          <span>已中奖 {{ currentDraws.length }} 人</span>
        </div>

        <div class="lottery-results-winners">
          <div class="lottery-results-winners-heading">
            <p class="section-kicker">WINNERS</p>
            <strong>中奖人</strong>
          </div>
          <div v-if="currentDraws.length" class="lottery-results-winner-list">
            <div v-for="draw in currentDraws" :key="draw.draw_id" class="lottery-results-winner-row">
              <span>第 {{ draw.draw_number }} 位</span>
              <strong>{{ draw.winner.username }}</strong>
            </div>
          </div>
          <p v-else class="lottery-results-no-winner">
            {{ isCurrentPrizeDrawing ? "开奖进行中" : "暂未开奖" }}
          </p>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  Button as VanButton,
  Empty as VanEmpty,
  Icon as VanIcon,
  Loading as VanLoading,
  Swipe as VanSwipe,
  SwipeItem as VanSwipeItem,
  Tag as VanTag,
} from "vant";
import {
  lotteryWebSocketURL,
  mediaURL,
  type Activity,
  type ActivityUserResponse,
  type MobileLotteryAward,
  type MobileLotteryDraw,
  type MobileLotteryPrize,
  type MobileLotteryRound,
  type MobileLotterySnapshot,
} from "../../api/client";

type ConnectionState = "connecting" | "connected" | "offline";
type StatusTagType = "primary" | "success" | "danger";
type ViewerPrize = MobileLotteryPrize & { award_name: string };
type ViewerAwardConfig = Pick<MobileLotteryAward, "award_id" | "name" | "sort_order">;

const props = defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const router = useRouter();
const activityId = props.activity.activity_id;
const loading = ref(true);
const error = ref("");
const connectionState = ref<ConnectionState>("connecting");
const snapshot = ref<MobileLotterySnapshot>();
const activeRound = ref<MobileLotteryRound>();
const activeIndex = ref(0);
const failedImageURLs = ref(new Set<string>());
let socket: WebSocket | undefined;
let reconnectTimer: number | undefined;
let pingTimer: number | undefined;
let reconnectAttempt = 0;
let stopped = false;

const prizes = computed<ViewerPrize[]>(() => {
  const awards = [...(snapshot.value?.awards || [])].sort(
    (left, right) => left.sort_order - right.sort_order || left.award_id - right.award_id,
  );
  return awards.flatMap((award) => [...award.prizes]
    .filter((prize) => prize.is_enabled)
    .sort((left, right) => left.sort_order - right.sort_order || left.prize_id - right.prize_id)
    .map((prize) => ({ ...prize, award_name: award.name })));
});
const currentPrize = computed(() => prizes.value[activeIndex.value]);
const currentDraws = computed(() => {
  const prizeId = currentPrize.value?.prize_id;
  if (!prizeId) return [];
  return [...(snapshot.value?.draws || [])]
    .filter((draw) => draw.prize_id === prizeId)
    .sort((left, right) => left.draw_id - right.draw_id);
});
const currentPrizeStatus = computed(() => {
  if (activeRound.value?.prize_id === currentPrize.value?.prize_id) return "drawing" as const;
  return currentDraws.value.length ? "drawn" as const : "pending" as const;
});
const isCurrentPrizeDrawing = computed(() => currentPrizeStatus.value === "drawing");
const currentPrizeStatusLabel = computed(() => ({
  drawing: "开奖中",
  drawn: "已开奖",
  pending: "待开奖",
}[currentPrizeStatus.value]));
const currentPrizeTagType = computed<StatusTagType>(() => (
  currentPrizeStatus.value === "drawing" ? "primary" : currentPrizeStatus.value === "drawn" ? "success" : "primary"
));
const activityStatus = computed(() => snapshot.value?.activity_status || props.activity.status);
const activityStatusLabel = computed(() => ({
  closed: "活动未开始",
  open: "活动进行中",
  ended: "活动已结束",
}[activityStatus.value]));
const activityTagType = computed<StatusTagType>(() => (
  activityStatus.value === "open" ? "success" : activityStatus.value === "ended" ? "danger" : "primary"
));
const connectionLabel = computed(() => ({
  connecting: "连接中",
  connected: "实时连接",
  offline: "重连中",
}[connectionState.value]));
const connectionTagType = computed<StatusTagType>(() => (
  connectionState.value === "connected" ? "success" : "primary"
));

const goHome = () => router.push({ name: "activity-home", params: { activityId } });
const prizeImageURL = (prize: ViewerPrize) => mediaURL(prize.image_url);
const canShowImage = (url: string | null) => Boolean(url && !failedImageURLs.value.has(url));
const markImageFailed = (url: string | null) => {
  if (!url) return;
  failedImageURLs.value = new Set([...failedImageURLs.value, url]);
};
const handleSlideChange = (index: number) => {
  activeIndex.value = index;
};

const normalizeActivePrize = (preferredPrizeId?: number) => {
  if (!prizes.value.length) {
    activeIndex.value = 0;
    return;
  }
  if (preferredPrizeId !== undefined) {
    const preferredIndex = prizes.value.findIndex((prize) => prize.prize_id === preferredPrizeId);
    activeIndex.value = preferredIndex >= 0 ? preferredIndex : 0;
    return;
  }
  activeIndex.value = Math.min(activeIndex.value, prizes.value.length - 1);
};

const applySnapshot = (nextSnapshot: MobileLotterySnapshot) => {
  const previousPrizeId = currentPrize.value?.prize_id;
  snapshot.value = nextSnapshot;
  activeRound.value = nextSnapshot.active_round || undefined;
  normalizeActivePrize(previousPrizeId ?? activeRound.value?.prize_id ?? nextSnapshot.selected_prize_id ?? undefined);
};

const applyConfigUpdate = (config: Record<string, unknown>) => {
  if (!snapshot.value || !Array.isArray(config.awards) || !Array.isArray(config.prizes)) return;
  const previousPrizeId = currentPrize.value?.prize_id;
  const draws = snapshot.value.draws;
  const awards = config.awards as ViewerAwardConfig[];
  const prizes = config.prizes as MobileLotteryPrize[];
  snapshot.value = {
    ...snapshot.value,
    config: {
      no_repeat_across_prizes: Boolean(config.no_repeat_across_prizes),
      rolling_name_count: Number(config.rolling_name_count),
    },
    awards: awards.map((award) => ({
      ...award,
      prizes: prizes.filter((prize) => prize.award_id === award.award_id),
      draws: draws.filter((draw) => draw.award_id === award.award_id),
    })),
  };
  normalizeActivePrize(previousPrizeId);
};

const appendDraw = (draw: MobileLotteryDraw) => {
  if (!snapshot.value || snapshot.value.draws.some((item) => item.draw_id === draw.draw_id)) return;
  const draws = [...snapshot.value.draws, draw].sort((left, right) => left.draw_id - right.draw_id);
  snapshot.value = {
    ...snapshot.value,
    latest_draw_id: Math.max(snapshot.value.latest_draw_id, draw.draw_id),
    draws,
    awards: snapshot.value.awards.map((award) => ({
      ...award,
      draws: draws.filter((item) => item.award_id === award.award_id),
      prizes: award.prizes.map((prize) => (
        prize.prize_id === draw.prize_id
          ? { ...prize, remaining_quantity: draw.remaining_quantity }
          : prize
      )),
    })),
  };
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
    connectionState.value = "connected";
    reconnectAttempt = 0;
    return;
  }
  if (payload.type === "lottery.config.updated" && payload.config) {
    applyConfigUpdate(payload.config as Record<string, unknown>);
    return;
  }
  if (payload.type === "lottery.prize.selected" && snapshot.value) {
    const prizeId = payload.selected_prize_id;
    if (typeof prizeId === "number" && Number.isInteger(prizeId) && prizeId > 0) {
      snapshot.value = { ...snapshot.value, selected_prize_id: prizeId };
    }
    return;
  }
  if (payload.type === "lottery.draw.started" && payload.round) {
    activeRound.value = payload.round as MobileLotteryRound;
    return;
  }
  if (payload.type === "lottery.draw.stopping") {
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if (roundId && activeRound.value?.round_id === roundId) {
      activeRound.value = { ...activeRound.value, phase: "stopping" };
    }
    return;
  }
  if (payload.type === "lottery.drawn" && payload.draw) {
    appendDraw(payload.draw as MobileLotteryDraw);
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if (!roundId || roundId === activeRound.value?.round_id) activeRound.value = undefined;
    return;
  }
  if (payload.type === "lottery.reset" && payload.snapshot) {
    applySnapshot(payload.snapshot as unknown as MobileLotterySnapshot);
    activeRound.value = undefined;
    return;
  }
  if (payload.type === "lottery.draw.error") {
    error.value = String(payload.detail || "抽奖状态暂时无法读取");
    if (payload.code === "activity_not_found") {
      stopped = true;
      loading.value = false;
      socket?.close();
    }
  }
};

const clearReconnectTimer = () => {
  if (reconnectTimer === undefined) return;
  window.clearTimeout(reconnectTimer);
  reconnectTimer = undefined;
};
const clearPingTimer = () => {
  if (pingTimer === undefined) return;
  window.clearInterval(pingTimer);
  pingTimer = undefined;
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
  connectionState.value = "connecting";
  const current = new WebSocket(lotteryWebSocketURL(activityId));
  socket = current;
  current.onopen = () => {
    connectionState.value = "connected";
    reconnectAttempt = 0;
    clearPingTimer();
    pingTimer = window.setInterval(() => {
      if (current.readyState === WebSocket.OPEN) current.send(JSON.stringify({ type: "lottery.ping" }));
    }, 15000);
  };
  current.onmessage = handleMessage;
  current.onerror = () => current.close();
  current.onclose = () => {
    if (socket !== current) return;
    socket = undefined;
    clearPingTimer();
    if (!stopped) {
      connectionState.value = "offline";
      scheduleReconnect();
    }
  };
}

const load = () => {
  stopped = true;
  clearReconnectTimer();
  clearPingTimer();
  socket?.close();
  socket = undefined;
  stopped = false;
  loading.value = true;
  error.value = "";
  reconnectAttempt = 0;
  connect();
};

onMounted(connect);
onBeforeUnmount(() => {
  stopped = true;
  clearReconnectTimer();
  clearPingTimer();
  socket?.close();
  socket = undefined;
});
</script>

<style scoped src="./lottery-results.css"></style>
