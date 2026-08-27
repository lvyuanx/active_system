<template>
  <main class="danmaku-overlay" :class="{ 'danmaku-overlay--standalone': !bootstrap }">
    <div v-if="bootstrap" class="danmaku-canvas" aria-live="off">
      <p
        v-for="item in activeItems"
        :key="item.key"
        class="danmaku-item"
        :style="item.style"
      >
        {{ item.body }}
      </p>
    </div>
    <section v-else class="danmaku-launch-placeholder">
      <span class="danmaku-launch-mark">A</span>
      <h1>弹幕渲染器</h1>
      <p>请从 ACTIVE 弹幕桌面工具启动。</p>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  danmakuWebSocketURL,
  getDanmakuMessages,
  type DanmakuMessage,
  type DanmakuOverlayBootstrap,
  type DanmakuSession,
  type DanmakuSettings,
} from "../../api/client";
import {
  addPendingRealtimeSignal,
  getReadyRecoveryAfterId,
  mergeOrderedMessages,
  removeResolvedRealtimeSignals,
} from "./message-order";

type ActiveItem = {
  key: string;
  body: string;
  style: Record<string, string>;
};
type DanmakuEvent = {
  type?: string;
  code?: string;
  message?: DanmakuMessage;
  settings?: DanmakuSettings;
  session?: DanmakuSession;
};

const MAX_PENDING_MESSAGES = 200;
const bootstrap = ref<DanmakuOverlayBootstrap>();
const settings = ref<DanmakuSettings>();
const activeItems = ref<ActiveItem[]>([]);
const pendingMessages = ref<DanmakuMessage[]>([]);
const lastMessageId = ref(0);
let socket: WebSocket | undefined;
let reconnectTimer: number | undefined;
let trackReleaseAt: number[] = [];
let itemSequence = 0;
let reconnectAttempt = 0;
let stopped = false;
let recovering = false;
let reconcilingRealtimeMessages = false;
let realtimeRetryTimer: number | undefined;
let pendingRealtimeMessageIds: number[] = [];
let unsubscribeOverlaySession: (() => void) | undefined;

const canRender = computed(() => Boolean(bootstrap.value && settings.value));

const resetTracks = () => {
  trackReleaseAt = Array.from({ length: settings.value?.track_count ?? 0 }, () => 0);
};
const setSettings = (next: DanmakuSettings) => {
  settings.value = next;
  resetTracks();
  flushQueue();
};
const clearRuntime = () => {
  activeItems.value = [];
  pendingMessages.value = [];
  resetTracks();
};
const stopSocket = () => {
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  if (realtimeRetryTimer) window.clearTimeout(realtimeRetryTimer);
  reconnectTimer = undefined;
  realtimeRetryTimer = undefined;
  socket?.close();
  socket = undefined;
};
const resetRuntime = (next: DanmakuOverlayBootstrap) => {
  stopped = false;
  recovering = false;
  reconcilingRealtimeMessages = false;
  pendingRealtimeMessageIds = [];
  reconnectAttempt = 0;
  stopSocket();
  bootstrap.value = next;
  lastMessageId.value = next.session.latest_message_id;
  setSettings(next.session.settings);
  clearRuntime();
  connect();
};
const queueMessage = (message: DanmakuMessage) => {
  if (!canRender.value || message.message_id <= lastMessageId.value) return;
  lastMessageId.value = message.message_id;
  if (pendingMessages.value.length >= MAX_PENDING_MESSAGES) pendingMessages.value.shift();
  pendingMessages.value.push(message);
  flushQueue();
};
const findAvailableTrack = (now: number) =>
  trackReleaseAt.findIndex((availableAt) => availableAt <= now);
const flushQueue = () => {
  if (!canRender.value || pendingMessages.value.length === 0) return;
  const now = Date.now();
  const track = findAvailableTrack(now);
  if (track < 0) {
    const nextAvailableAt = Math.min(...trackReleaseAt);
    window.setTimeout(flushQueue, Math.max(16, nextAvailableAt - now));
    return;
  }
  const message = pendingMessages.value.shift();
  if (!message || !settings.value) return;
  const currentSettings = settings.value;
  const displayHeight = currentSettings.display_bottom - currentSettings.display_top;
  const top = currentSettings.display_top + ((track + 0.5) / currentSettings.track_count) * displayHeight;
  const durationMilliseconds = currentSettings.duration_seconds * 1000;
  const key = `${message.message_id}-${itemSequence++}`;
  activeItems.value.push({
    key,
    body: message.body,
    style: {
      "--danmaku-top": `${top}%`,
      "--danmaku-font-size": `${currentSettings.font_size}px`,
      "--danmaku-opacity": String(currentSettings.opacity),
      "--danmaku-duration": `${currentSettings.duration_seconds}s`,
      "--danmaku-color": currentSettings.text_color,
    },
  });
  trackReleaseAt[track] = now + durationMilliseconds;
  window.setTimeout(() => {
    activeItems.value = activeItems.value.filter((item) => item.key !== key);
    flushQueue();
  }, durationMilliseconds);
  flushQueue();
};
const fetchMessagesAfter = async (afterId: number): Promise<DanmakuMessage[]> => {
  const activeBootstrap = bootstrap.value;
  if (!activeBootstrap) return [];
  let cursor = afterId;
  const recovered: DanmakuMessage[] = [];
  while (!stopped) {
    const page = await getDanmakuMessages(activeBootstrap.apiBaseUrl, activeBootstrap.token, cursor);
    if (bootstrap.value !== activeBootstrap) return [];
    recovered.push(...page.items);
    const latest = page.items.at(-1)?.message_id;
    if (!page.has_more || !latest || latest <= cursor) return recovered;
    cursor = latest;
  }
  return recovered;
};
const applyOrderedMessages = (messages: DanmakuMessage[]) => {
  mergeOrderedMessages(lastMessageId.value, messages).forEach(queueMessage);
};
const scheduleRealtimeRetry = () => {
  if (realtimeRetryTimer || stopped || recovering || pendingRealtimeMessageIds.length === 0) return;
  realtimeRetryTimer = window.setTimeout(() => {
    realtimeRetryTimer = undefined;
    void reconcileRealtimeMessages();
  }, 500);
};
const reconcileRealtimeMessages = async () => {
  if (reconcilingRealtimeMessages || recovering || stopped || !bootstrap.value) return;
  reconcilingRealtimeMessages = true;
  try {
    while (!stopped && pendingRealtimeMessageIds.length > 0) {
      const messages = await fetchMessagesAfter(lastMessageId.value);
      if (messages.length === 0) return;
      applyOrderedMessages(messages);
      pendingRealtimeMessageIds = removeResolvedRealtimeSignals(pendingRealtimeMessageIds, lastMessageId.value);
    }
  } catch {
    // Keep the event IDs pending so a temporary HTTP failure cannot skip live messages.
  } finally {
    reconcilingRealtimeMessages = false;
    scheduleRealtimeRetry();
  }
};
const handleReady = async (session: DanmakuSession, ws: WebSocket) => {
  setSettings(session.settings);
  const recoveryCursor = getReadyRecoveryAfterId(lastMessageId.value, session.latest_message_id);
  recovering = true;
  let recoveredCompletely = false;
  try {
    applyOrderedMessages(await fetchMessagesAfter(recoveryCursor));
    recoveredCompletely = true;
  } catch {
    // Keep the prior cursor so the next WebSocket session retries the complete missed range.
    ws.close(1012, "弹幕补齐失败，正在重连");
  } finally {
    recovering = false;
    if (!recoveredCompletely) {
      pendingRealtimeMessageIds = [];
      return;
    }
    pendingRealtimeMessageIds = removeResolvedRealtimeSignals(pendingRealtimeMessageIds, lastMessageId.value);
    void reconcileRealtimeMessages();
  }
};
const connect = () => {
  if (stopped || !bootstrap.value) return;
  const currentBootstrap = bootstrap.value;
  const ws = new WebSocket(danmakuWebSocketURL(currentBootstrap.apiBaseUrl));
  socket = ws;
  ws.onopen = () => {
    reconnectAttempt = 0;
    ws.send(JSON.stringify({ type: "auth", token: currentBootstrap.token }));
  };
  ws.onmessage = (event) => {
    let payload: DanmakuEvent;
    try {
      payload = JSON.parse(event.data) as DanmakuEvent;
    } catch {
      return;
    }
    if (payload.type === "danmaku.ready" && payload.session) void handleReady(payload.session, ws);
    if (payload.type === "danmaku.message.created" && payload.message) {
      if (payload.message.message_id > lastMessageId.value) {
        pendingRealtimeMessageIds = addPendingRealtimeSignal(
          pendingRealtimeMessageIds,
          payload.message.message_id,
        );
        void reconcileRealtimeMessages();
      }
    }
    if (payload.type === "danmaku.settings.updated" && payload.settings) setSettings(payload.settings);
    if (payload.type === "danmaku.error" && payload.code === "unauthorized") {
      stopped = true;
      ws.close();
    }
  };
  ws.onclose = (event) => {
    if (event.code === 4001) {
      stopped = true;
      return;
    }
    if (stopped || socket !== ws) return;
    const delay = Math.min(10_000, 1_000 * 2 ** reconnectAttempt++);
    reconnectTimer = window.setTimeout(connect, delay);
  };
  ws.onerror = () => ws.close();
};

onMounted(async () => {
  const bridge = window.danmakuDesktop;
  if (!bridge) return;
  unsubscribeOverlaySession = bridge.onOverlaySession(resetRuntime);
  const initial = await bridge.getOverlaySession();
  if (initial) resetRuntime(initial);
});
onBeforeUnmount(() => {
  stopped = true;
  unsubscribeOverlaySession?.();
  stopSocket();
});
</script>

<style scoped>
.danmaku-overlay {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  pointer-events: none;
}

.danmaku-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.danmaku-item {
  position: absolute;
  top: var(--danmaku-top);
  left: 100%;
  margin: 0;
  color: var(--danmaku-color);
  font-size: var(--danmaku-font-size);
  font-weight: 750;
  line-height: 1.2;
  opacity: var(--danmaku-opacity);
  text-shadow: 0 2px 4px rgb(0 0 0 / 70%);
  white-space: nowrap;
  will-change: transform;
  animation: danmaku-fly var(--danmaku-duration) linear forwards;
}

.danmaku-launch-placeholder {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  width: min(100% - 48px, 480px);
  min-height: 100vh;
  margin: 0 auto;
  color: #dfe9e4;
  text-align: center;
}

.danmaku-launch-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  color: #17211e;
  background: #77d2b5;
  border-radius: 6px;
  font-size: 23px;
  font-weight: 800;
}

.danmaku-launch-placeholder h1 {
  margin: 6px 0 0;
  font-size: 22px;
}

.danmaku-launch-placeholder p {
  margin: 0;
  color: #9daea6;
  font-size: 14px;
}

.danmaku-overlay--standalone {
  background: #07111f;
}

@keyframes danmaku-fly {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(calc(-100vw - 100%));
  }
}

@media (prefers-reduced-motion: reduce) {
  .danmaku-item {
    animation-duration: 0.01ms !important;
  }
}
</style>
