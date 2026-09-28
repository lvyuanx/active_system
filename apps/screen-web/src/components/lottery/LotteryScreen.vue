<template>
  <main
    class="lottery-screen"
    :class="{
      'lottery-screen--round-active': activeRound,
      'lottery-screen--immersive': activeRound,
    }"
    :data-lottery-phase="globePhase"
  >
    <div class="aurora aurora-one"></div>
    <div class="aurora aurora-two"></div>
    <div class="particle-field" aria-hidden="true">
      <i v-for="index in 18" :key="index" :style="particleStyle(index)"></i>
    </div>

    <header class="lottery-header">
      <div class="brand">
        <span class="brand-mark">A</span>
        <span><strong>ACTIVE</strong><small>LIVE LOTTERY</small></span>
      </div>
      <div class="connection-state" :class="{ 'connection-state--online': connected }">
        <i></i>{{ connected ? "实时连接" : "正在重连" }}
      </div>
    </header>

    <section class="lottery-content">
      <div class="title-block">
        <div class="title-prize">
          <img
            v-if="displayPrizeImageURL && canShowImage(displayPrizeImageURL)"
            class="title-prize__image"
            :src="imageURL(displayPrizeImageURL)"
            alt=""
            @error="markImageFailed(displayPrizeImageURL)"
          />
          <h1>{{ displayPrizeName || "等待奖品" }}</h1>
        </div>
      </div>

      <div class="draw-layout" :class="{ 'draw-layout--active': activeRound }">
        <section
          class="reveal-panel"
          :class="{ 'reveal-panel--rolling': rolling || activeRound }"
          aria-live="polite"
        >
          <div class="reveal-beam"></div>
          <p class="reveal-label">{{ revealLabel }}</p>
          <div v-if="activeRound" class="globe-stage">
            <LotteryGlobe
              :participants="activeRound.participants"
              :phase="globePhase"
              :winner-id="pendingDraw?.winner.activity_user_id"
              :winner="pendingDraw?.winner"
              :round-id="activeRound.round_id"
              :started-at="activeRound.started_at"
              @scattered="handleGlobeScattered"
              @settled="handleGlobeSettled"
            />
            <div class="round-prize-chip">
              <img
                v-if="activePrizeImageURL && canShowImage(activePrizeImageURL)"
                class="round-prize-chip__image"
                :src="imageURL(activePrizeImageURL)"
                alt=""
                @error="markImageFailed(activePrizeImageURL)"
              />
              <span>{{ activeRound.award_name }} · {{ activeRound.prize_name }}</span>
            </div>
          </div>
          <div v-else class="name-stage">
            <div v-if="rolling" class="rolling-names">
              <span
                v-for="(name, index) in rollingNames"
                :key="`${name}-${index}`"
                :class="{ 'name-focus': index === rollingNames.length - 1 }"
              >
                {{ name }}
              </span>
            </div>
            <div v-else-if="currentDraw" class="winner-result">
              <img class="winner-result__avatar" :src="currentWinnerAvatarSource" alt="" />
              <div class="winner-name">{{ currentDraw.winner.username }}</div>
            </div>
            <div v-else class="waiting-mark">✦</div>
          </div>
          <div v-if="currentDraw && !activeRound" class="winner-meta">
            <span>{{ currentDraw.award_name }}</span>
            <b>第 {{ currentDraw.draw_number }} 位</b>
            <span>剩余 {{ currentDraw.remaining_quantity }}</span>
          </div>
          <p v-if="error" class="reveal-tip">{{ error }}</p>
          <p v-else-if="!activeRound && !currentDraw" class="reveal-tip">大屏已就绪 · 等待管理端发起开奖</p>
        </section>

        <aside class="prize-board">
          <header><span class="board-kicker">PRIZE BOARD</span><strong>奖项进度</strong></header>
          <div v-if="!snapshot?.awards.length" class="board-empty">暂无奖项配置</div>
          <article v-for="award in snapshot?.awards || []" :key="award.award_id" class="award-card">
            <div class="award-heading">
              <span>{{ award.name }}</span><small>{{ award.draws.length }} 人已中奖</small>
            </div>
            <div v-for="prize in award.prizes" :key="prize.prize_id" class="prize-item">
              <div class="prize-line">
                <img
                  v-if="prize.image_url && canShowImage(prize.image_url)"
                  class="prize-image"
                  :src="imageURL(prize.image_url)"
                  alt=""
                  @error="markImageFailed(prize.image_url)"
                />
                <span>{{ prize.name }}</span><b>{{ prize.remaining_quantity }}<small>/{{ prize.quantity }}</small></b>
              </div>
              <div v-if="prizeDraws(award, prize.prize_id).length" class="winner-list">
                <span
                  v-for="draw in prizeDraws(award, prize.prize_id)"
                  :key="draw.draw_id"
                >{{ draw.winner.username }}</span>
              </div>
            </div>
          </article>
        </aside>
      </div>

      <footer class="lottery-footer">
        <span>LIVE · {{ footerText }}</span>
        <span v-if="snapshot">已揭晓 {{ snapshot.draws.length }} 人</span>
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  baseURL,
  lotteryWebSocketURL,
  type LotteryDraw,
  type LotteryDrawnEvent,
  type LotteryRound,
  type LotteryRoundParticipant,
  type LotterySnapshot,
} from "../../api/client";
import { enqueueLotteryDraw, readyLotteryDrawIds } from "./lottery-order";
import { latestLotteryDrawForPrize } from "./lottery-selection";
import { avatarSources } from "./avatar-sources";
import LotteryGlobe from "./LotteryGlobe.vue";

const props = defineProps<{ activityId: string; apiBaseUrl?: string }>();
const apiBaseUrl = props.apiBaseUrl || baseURL;
const snapshot = ref<LotterySnapshot>();
const queue = ref<LotteryDraw[]>([]);
const currentDraw = ref<LotteryDraw>();
const currentWinnerAvatarId = ref(1);
const rollingNames = ref<string[]>([]);
const activeRound = ref<LotteryRound>();
const selectedPrizeId = ref<number>();
const pendingDraw = ref<LotteryDraw>();
const globeSettled = ref(false);
const roundQueue = ref<LotteryRound[]>([]);
type GlobeStage = "rolling" | "scattering" | "scattered" | "selecting" | "revealed";
const globeStage = ref<GlobeStage>("rolling");
const connected = ref(false);
const rolling = ref(false);
const error = ref("");
let knownDrawIds = new Set<number>();
let socket: WebSocket | undefined;
let reconnectTimer: number | undefined;
let revealTimer: number | undefined;
let restoreTimer: number | undefined;
let pingTimer: number | undefined;
let retryCount = 0;
let stopped = false;
const rollNamesByDraw = new Map<number, string[]>();
const drawsByRound = new Map<string, LotteryDraw>();
const stoppingRoundIds = new Set<string>();
const failedImageURLs = ref(new Set<string>());

const globePhase = computed(() => {
  if (!activeRound.value) return "idle" as const;
  return globeStage.value;
});
const revealLabel = computed(() => {
  if (!activeRound.value) return currentDraw.value ? "WINNER REVEALED" : "READY TO DRAW";
  return ({
    rolling: "ALL USERS ROLLING",
    scattering: "SCATTERING USERS",
    scattered: "WINNER PENDING",
    selecting: "WINNER FOCUS",
    revealed: "WINNER REVEALED",
  }[globeStage.value]);
});
const footerText = computed(() => (
  activeRound.value
    ? globeStage.value === "revealed" ? "中奖结果已揭晓" : "抽奖动画进行中"
    : queue.value.length ? `${queue.value.length} 个结果排队中` : "抽奖结果实时同步"
));

const imageURL = (url: string | null) => {
  if (!url) return undefined;
  const origin = new URL(apiBaseUrl, window.location.origin).origin;
  return new URL(url, origin).toString();
};
const canShowImage = (url: string | null) => Boolean(url && !failedImageURLs.value.has(url));
const markImageFailed = (url: string | null) => {
  if (!url) return;
  failedImageURLs.value = new Set([...failedImageURLs.value, url]);
};

const activePrizeImageURL = computed(() => {
  const round = activeRound.value;
  if (!round) return null;
  return snapshot.value?.awards
    .find((award) => award.award_id === round.award_id)
    ?.prizes.find((prize) => prize.prize_id === round.prize_id)?.image_url || null;
});

const selectedPrize = computed(() => {
  const prizes = snapshot.value?.awards.flatMap((award) => award.prizes) || [];
  return prizes.find((item) => item.prize_id === selectedPrizeId.value)
    || prizes.find((item) => item.remaining_quantity > 0);
});
const selectedPrizeName = computed(() => selectedPrize.value?.name);
const displayPrizeName = computed(() => (
  activeRound.value?.prize_name || selectedPrizeName.value || currentDraw.value?.prize_name
));
const displayPrizeImageURL = computed(() => {
  if (activeRound.value) return activePrizeImageURL.value;
  if (selectedPrize.value) return selectedPrize.value.image_url || null;
  if (currentDraw.value) return currentDraw.value.prize_image_url;
  return null;
});
const currentWinnerAvatarSource = computed(() => avatarSources[currentWinnerAvatarId.value] || avatarSources[1]);

const fallbackWinnerAvatarId = (activityUserId: number) => {
  const normalizedId = Math.max(1, Math.abs(Math.trunc(activityUserId)));
  return ((normalizedId - 1) % Object.keys(avatarSources).length) + 1;
};
const rememberWinnerAvatar = (draw: LotteryDraw, participants: LotteryRoundParticipant[] = []) => {
  const participant = participants.find((item) => item.activity_user_id === draw.winner.activity_user_id);
  currentWinnerAvatarId.value = participant?.avatar_id || fallbackWinnerAvatarId(draw.winner.activity_user_id);
};
const syncCurrentDrawToSelectedPrize = (prizeId: number | undefined) => {
  const draw = latestLotteryDrawForPrize(snapshot.value?.draws || [], prizeId);
  currentDraw.value = draw;
  if (draw) rememberWinnerAvatar(draw);
  else currentWinnerAvatarId.value = 1;
};

const clearRestoreTimer = () => {
  if (restoreTimer === undefined) return;
  window.clearTimeout(restoreTimer);
  restoreTimer = undefined;
};

watch(
  () => snapshot.value?.activity_name,
  (activityName) => {
    document.title = activityName?.trim() || "幸运抽奖";
  },
  { immediate: true },
);

const particleStyle = (index: number) => ({
  "--particle-x": `${(index * 37) % 100}%`,
  "--particle-y": `${(index * 61) % 100}%`,
  "--particle-delay": `${(index % 7) * 0.7}s`,
});

const appendDraw = (draw: LotteryDraw) => {
  if (!snapshot.value || snapshot.value.draws.some((item) => item.draw_id === draw.draw_id)) return;
  snapshot.value.draws = [...snapshot.value.draws, draw].sort(
    (left, right) => left.draw_id - right.draw_id,
  );
  const award = snapshot.value.awards.find((item) => item.award_id === draw.award_id);
  const prize = award?.prizes.find((item) => item.prize_id === draw.prize_id);
  if (prize) prize.remaining_quantity = draw.remaining_quantity;
  if (award && !award.draws.some((item) => item.draw_id === draw.draw_id)) award.draws.push(draw);
};

const prizeDraws = (award: LotterySnapshot["awards"][number], prizeId: number) => (
  award.draws.filter((draw) => draw.prize_id === prizeId).slice(-4).reverse()
);

const activateRound = (round: LotteryRound) => {
  clearRestoreTimer();
  const isStopping = round.phase === "stopping" || stoppingRoundIds.has(round.round_id);
  stoppingRoundIds.delete(round.round_id);
  activeRound.value = isStopping ? { ...round, phase: "stopping" } : round;
  pendingDraw.value = drawsByRound.get(round.round_id);
  drawsByRound.delete(round.round_id);
  globeSettled.value = false;
  globeStage.value = isStopping ? "scattering" : "rolling";
};

const queueRound = (round: LotteryRound) => {
  if (
    roundQueue.value.some((item) => item.round_id === round.round_id)
    || activeRound.value?.round_id === round.round_id
  ) return;
  roundQueue.value.push(round);
};

const activateQueuedRound = () => {
  const nextRound = roundQueue.value.shift();
  if (nextRound) activateRound(nextRound);
};

const handleGlobeScattered = () => {
  globeStage.value = pendingDraw.value ? "selecting" : "scattered";
};

const handleGlobeSettled = () => {
  if (!pendingDraw.value) return;
  globeStage.value = "revealed";
  globeSettled.value = true;
  currentDraw.value = pendingDraw.value;
  rememberWinnerAvatar(pendingDraw.value, activeRound.value?.participants);
  if (roundQueue.value.length) activateQueuedRound();
  else {
    const duration = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? 700 : 2200;
    restoreTimer = window.setTimeout(() => {
      restoreTimer = undefined;
      activeRound.value = undefined;
      pendingDraw.value = undefined;
      globeSettled.value = false;
      globeStage.value = "rolling";
      syncCurrentDrawToSelectedPrize(selectedPrizeId.value);
    }, duration);
  }
};

const playNext = () => {
  if (rolling.value || !queue.value.length) return;
  const draw = queue.value.shift();
  if (!draw) return;
  rolling.value = true;
  rollingNames.value = rollNamesByDraw.get(draw.draw_id) || [draw.winner.username];
  rollNamesByDraw.delete(draw.draw_id);
  revealTimer = window.setTimeout(() => {
    currentDraw.value = draw;
    rememberWinnerAvatar(draw);
    rolling.value = false;
    appendDraw(draw);
    revealTimer = window.setTimeout(() => {
      revealTimer = undefined;
      playNext();
    }, 450);
  }, 3000);
};

const handleReady = (ready: LotterySnapshot) => {
  if (revealTimer !== undefined) {
    window.clearTimeout(revealTimer);
    revealTimer = undefined;
  }
  clearRestoreTimer();
  snapshot.value = ready;
  knownDrawIds = readyLotteryDrawIds(ready.draws);
  queue.value = [];
  roundQueue.value = [];
  drawsByRound.clear();
  rollNamesByDraw.clear();
  stoppingRoundIds.clear();
  error.value = "";
  activeRound.value = ready.active_round || undefined;
  selectedPrizeId.value = typeof ready.selected_prize_id === "number"
    ? ready.selected_prize_id
    : activeRound.value?.prize_id;
  if (activeRound.value) {
    currentDraw.value = undefined;
    currentWinnerAvatarId.value = 1;
  } else {
    syncCurrentDrawToSelectedPrize(selectedPrizeId.value);
  }
  pendingDraw.value = undefined;
  globeSettled.value = false;
  globeStage.value = activeRound.value?.phase === "stopping" ? "scattering" : "rolling";
  rolling.value = false;
  rollingNames.value = [];
};

const applyConfigUpdate = (payload: Record<string, unknown>) => {
  if (!snapshot.value || !payload.awards || !payload.prizes) return;
  const awards = payload.awards as LotterySnapshot["awards"];
  const prizes = payload.prizes as LotterySnapshot["awards"][number]["prizes"];
  snapshot.value.config = {
    no_repeat_across_prizes: Boolean(payload.no_repeat_across_prizes),
    rolling_name_count: Number(payload.rolling_name_count),
  };
  snapshot.value.awards = awards.map((award) => ({
    ...award,
    prizes: prizes.filter((prize) => prize.award_id === award.award_id),
    draws: snapshot.value?.draws.filter((draw) => draw.award_id === award.award_id) || [],
  }));
};

const handleMessage = (event: MessageEvent<string>) => {
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(event.data) as Record<string, unknown>;
  } catch {
    return;
  }
  if (payload.type === "lottery.ready") {
    handleReady(payload as unknown as LotterySnapshot);
  } else if (payload.type === "lottery.prize.selected") {
    const prizeId = payload.selected_prize_id;
    if (typeof prizeId === "number" && Number.isInteger(prizeId) && prizeId > 0) {
      selectedPrizeId.value = prizeId;
      if (!activeRound.value && !rolling.value) syncCurrentDrawToSelectedPrize(prizeId);
    }
  } else if (payload.type === "lottery.draw.started" && payload.round) {
    const round = payload.round as LotteryRound;
    if (!Array.isArray(round.participants)) return;
    selectedPrizeId.value = round.prize_id;
    const normalizedRound = stoppingRoundIds.has(round.round_id) ? { ...round, phase: "stopping" as const } : round;
    if (activeRound.value && !globeSettled.value) queueRound(normalizedRound);
    else activateRound(normalizedRound);
  } else if (payload.type === "lottery.draw.stopping") {
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if (!roundId) return;
    stoppingRoundIds.add(roundId);
    if (activeRound.value?.round_id === roundId) {
      activeRound.value = { ...activeRound.value, phase: "stopping" };
      globeStage.value = "scattering";
      stoppingRoundIds.delete(roundId);
    }
  } else if (payload.type === "lottery.drawn" && payload.draw) {
    const drawn = payload as unknown as LotteryDrawnEvent;
    if (knownDrawIds.has(drawn.draw.draw_id)) return;
    const roundId = drawn.round_id;
    if (roundId) {
      selectedPrizeId.value = drawn.draw.prize_id;
      knownDrawIds.add(drawn.draw.draw_id);
      appendDraw(drawn.draw);
      if (activeRound.value?.round_id === roundId) {
        pendingDraw.value = drawn.draw;
        globeSettled.value = false;
        if (globeStage.value === "rolling") globeStage.value = "scattering";
        else if (globeStage.value === "scattered") globeStage.value = "selecting";
      } else {
        drawsByRound.set(roundId, drawn.draw);
        if (!activeRound.value) {
          currentDraw.value = drawn.draw;
          rememberWinnerAvatar(drawn.draw);
        }
      }
    } else {
      selectedPrizeId.value = drawn.draw.prize_id;
      rollNamesByDraw.set(drawn.draw.draw_id, drawn.roll_names || []);
      queue.value = enqueueLotteryDraw(knownDrawIds, queue.value, drawn.draw);
      rollingNames.value = drawn.roll_names || [];
    }
    error.value = "";
    if (!roundId) playNext();
  } else if (payload.type === "lottery.config.updated" && payload.config) {
    applyConfigUpdate(payload.config as Record<string, unknown>);
  } else if (payload.type === "lottery.reset" && payload.snapshot) {
    if (revealTimer !== undefined) {
      window.clearTimeout(revealTimer);
      revealTimer = undefined;
    }
    clearRestoreTimer();
    handleReady(payload.snapshot as LotterySnapshot);
    currentDraw.value = undefined;
    currentWinnerAvatarId.value = 1;
    activeRound.value = undefined;
    pendingDraw.value = undefined;
    roundQueue.value = [];
    drawsByRound.clear();
    stoppingRoundIds.clear();
    globeStage.value = "rolling";
    rolling.value = false;
    rollingNames.value = [];
    rollNamesByDraw.clear();
  } else if (payload.type === "lottery.draw.error") {
    error.value = String(payload.detail || "开奖暂时失败");
    const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
    if ((roundId && activeRound.value?.round_id === roundId) || payload.code === "activity_not_found") {
      clearRestoreTimer();
      activeRound.value = undefined;
      pendingDraw.value = undefined;
      globeSettled.value = false;
      roundQueue.value = [];
      if (roundId) stoppingRoundIds.delete(roundId);
      globeStage.value = "rolling";
    }
    if (roundId) drawsByRound.delete(roundId);
    if (payload.code === "activity_not_found") {
      stopped = true;
      socket?.close();
    }
  }
};

const scheduleReconnect = () => {
  if (stopped || reconnectTimer !== undefined) return;
  retryCount += 1;
  const delay = Math.min(8000, 500 * 2 ** Math.min(retryCount - 1, 4));
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = undefined;
    connect();
  }, delay);
};

const connect = () => {
  if (stopped) return;
  const current = new WebSocket(lotteryWebSocketURL(apiBaseUrl, props.activityId));
  socket = current;
  current.onopen = () => {
    retryCount = 0;
    connected.value = true;
    pingTimer = window.setInterval(() => {
      if (current.readyState === WebSocket.OPEN) {
        current.send(JSON.stringify({ type: "lottery.ping" }));
      }
    }, 15000);
  };
  current.onmessage = handleMessage;
  current.onerror = () => current.close();
  current.onclose = () => {
    if (socket !== current) return;
    connected.value = false;
    if (pingTimer !== undefined) window.clearInterval(pingTimer);
    pingTimer = undefined;
    scheduleReconnect();
  };
};

onMounted(connect);
onBeforeUnmount(() => {
  stopped = true;
  if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
  if (revealTimer !== undefined) window.clearTimeout(revealTimer);
  clearRestoreTimer();
  if (pingTimer !== undefined) window.clearInterval(pingTimer);
  socket?.close();
});
</script>

<style scoped src="./LotteryScreen.css"></style>
<style scoped src="./LotteryScreenImages.css"></style>
