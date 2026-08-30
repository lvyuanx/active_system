<template>
  <main class="lottery-screen">
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
        <p class="kicker">SPECIAL EVENT · LUCKY DRAW</p>
        <h1>{{ snapshot?.activity_name || "幸运抽奖" }}</h1>
        <p class="subtitle">{{ error || "好运正在聚集，下一位幸运者即将揭晓" }}</p>
      </div>

      <div class="draw-layout">
        <section class="reveal-panel" :class="{ 'reveal-panel--rolling': rolling }" aria-live="polite">
          <div class="reveal-beam"></div>
          <p class="reveal-label">
            {{ rolling ? "LUCKY NAME ROLLING" : currentDraw ? "WINNER REVEALED" : "READY TO DRAW" }}
          </p>
          <img
            v-if="currentDraw?.prize_image_url && canShowImage(currentDraw.prize_image_url)"
            class="winner-prize-image"
            :src="imageURL(currentDraw.prize_image_url)"
            alt="中奖奖品"
            @error="markImageFailed(currentDraw.prize_image_url)"
          />
          <h2>{{ currentDraw?.prize_name || selectedPrizeName || "等待抽奖" }}</h2>
          <div class="name-stage">
            <div v-if="rolling" class="rolling-names">
              <span
                v-for="(name, index) in rollingNames"
                :key="`${name}-${index}`"
                :class="{ 'name-focus': index === rollingNames.length - 1 }"
              >
                {{ name }}
              </span>
            </div>
            <div v-else-if="currentDraw" class="winner-name">{{ currentDraw.winner.username }}</div>
            <div v-else class="waiting-mark">✦</div>
          </div>
          <div v-if="currentDraw" class="winner-meta">
            <span>{{ currentDraw.award_name }}</span>
            <b>第 {{ currentDraw.draw_number }} 位</b>
            <span>剩余 {{ currentDraw.remaining_quantity }}</span>
          </div>
          <p v-else class="reveal-tip">大屏已就绪 · 等待管理端发起开奖</p>
        </section>

        <aside class="prize-board">
          <header><span class="board-kicker">PRIZE BOARD</span><strong>奖项进度</strong></header>
          <div v-if="!snapshot?.awards.length" class="board-empty">暂无奖项配置</div>
          <article v-for="award in snapshot?.awards || []" :key="award.award_id" class="award-card">
            <div class="award-heading">
              <span>{{ award.name }}</span><small>{{ award.draws.length }} 人已中奖</small>
            </div>
            <div v-for="prize in award.prizes" :key="prize.prize_id" class="prize-line">
              <img
                v-if="prize.image_url && canShowImage(prize.image_url)"
                class="prize-image"
                :src="imageURL(prize.image_url)"
                alt=""
                @error="markImageFailed(prize.image_url)"
              />
              <span>{{ prize.name }}</span><b>{{ prize.remaining_quantity }}<small>/{{ prize.quantity }}</small></b>
            </div>
            <div v-if="award.draws.length" class="winner-list">
              <span
                v-for="draw in award.draws.slice(-4).reverse()"
                :key="draw.draw_id"
              >{{ draw.winner.username }}</span>
            </div>
          </article>
        </aside>
      </div>

      <footer class="lottery-footer">
        <span>LIVE · {{ queue.length ? `${queue.length} 个结果排队中` : "抽奖结果实时同步" }}</span>
        <span v-if="snapshot">已揭晓 {{ snapshot.draws.length }} 人</span>
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  lotteryWebSocketURL,
  type LotteryDraw,
  type LotteryDrawnEvent,
  type LotterySnapshot,
} from "../../api/client";
import { enqueueLotteryDraw, readyLotteryDrawIds } from "./lottery-order";

const props = defineProps<{ activityId: string; apiBaseUrl?: string }>();
const apiBaseUrl = props.apiBaseUrl
  || (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1");
const snapshot = ref<LotterySnapshot>();
const queue = ref<LotteryDraw[]>([]);
const currentDraw = ref<LotteryDraw>();
const rollingNames = ref<string[]>([]);
const connected = ref(false);
const rolling = ref(false);
const error = ref("");
let knownDrawIds = new Set<number>();
let socket: WebSocket | undefined;
let reconnectTimer: number | undefined;
let revealTimer: number | undefined;
let pingTimer: number | undefined;
let retryCount = 0;
let stopped = false;
const rollNamesByDraw = new Map<number, string[]>();
const failedImageURLs = ref(new Set<string>());

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

const selectedPrizeName = computed(() => {
  const prize = snapshot.value?.awards
    .flatMap((award) => award.prizes)
    .find((item) => item.remaining_quantity > 0);
  return prize?.name;
});

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

const playNext = () => {
  if (rolling.value || !queue.value.length) return;
  const draw = queue.value.shift();
  if (!draw) return;
  rolling.value = true;
  rollingNames.value = rollNamesByDraw.get(draw.draw_id) || [draw.winner.username];
  rollNamesByDraw.delete(draw.draw_id);
  revealTimer = window.setTimeout(() => {
    currentDraw.value = draw;
    rolling.value = false;
    appendDraw(draw);
    revealTimer = window.setTimeout(() => {
      revealTimer = undefined;
      playNext();
    }, 450);
  }, 3000);
};

const handleReady = (ready: LotterySnapshot) => {
  snapshot.value = ready;
  knownDrawIds = readyLotteryDrawIds(ready.draws);
  queue.value = [];
  rollNamesByDraw.clear();
  error.value = "";
  if (currentDraw.value && !knownDrawIds.has(currentDraw.value.draw_id)) {
    currentDraw.value = undefined;
  }
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
  } else if (payload.type === "lottery.drawn" && payload.draw) {
    const drawn = payload as unknown as LotteryDrawnEvent;
    rollNamesByDraw.set(drawn.draw.draw_id, drawn.roll_names);
    queue.value = enqueueLotteryDraw(knownDrawIds, queue.value, drawn.draw);
    rollingNames.value = drawn.roll_names;
    error.value = "";
    playNext();
  } else if (payload.type === "lottery.config.updated" && payload.config) {
    applyConfigUpdate(payload.config as Record<string, unknown>);
  } else if (payload.type === "lottery.reset" && payload.snapshot) {
    if (revealTimer !== undefined) {
      window.clearTimeout(revealTimer);
      revealTimer = undefined;
    }
    handleReady(payload.snapshot as LotterySnapshot);
    currentDraw.value = undefined;
    rolling.value = false;
    rollingNames.value = [];
    rollNamesByDraw.clear();
  } else if (payload.type === "lottery.draw.error") {
    error.value = String(payload.detail || "开奖暂时失败");
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
  if (pingTimer !== undefined) window.clearInterval(pingTimer);
  socket?.close();
});
</script>

<style scoped src="./LotteryScreen.css"></style>
<style scoped src="./LotteryScreenImages.css"></style>
