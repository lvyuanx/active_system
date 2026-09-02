<template>
  <main class="danmaku-overlay" :class="{ 'danmaku-overlay--standalone': !bootstrap }">
    <div v-if="bootstrap" class="danmaku-canvas" aria-live="off">
      <p
        v-for="item in activeItems"
        :key="item.key"
        class="danmaku-item"
        :class="{ 'danmaku-item--sticker': Boolean(item.sticker) }"
        :style="item.style"
      >
        <img
          v-if="item.sticker && !item.imageFailed"
          class="danmaku-sticker"
          :src="resolveImageURL(item.sticker.image_url)"
          :alt="item.sticker.name"
          @error="markImageFailed(item.key)"
        />
        <span v-else>{{ item.body }}</span>
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
import "./DanmakuOverlay.css";
import {
  danmakuWebSocketURL,
  getDanmakuMessages,
  type DanmakuMessage,
  type DanmakuOverlayBootstrap,
  type DanmakuSession,
  type DanmakuSettings,
} from "../../api/client";
import {
  addPendingRealtimeMessage,
  getReadyRecoveryAfterId,
  getRealtimeMessageDecision,
  mergeOrderedMessages,
  removeResolvedRealtimeMessages,
  takeContiguousRealtimeMessages,
} from "./message-order";
import {
  DANMAKU_GAP_PX,
  DANMAKU_STICKER_HEIGHT_MULTIPLIER,
  findSafeTrack,
  isPendingMessageExpired,
  measureDanmakuImageWidth,
  measureDanmakuText,
  type DanmakuMotion,
} from "./danmaku-layout";
import { createTaskScheduler, type ScheduledTaskId } from "./task-scheduler";

type ActiveItem = {
  key: string;
  body: string;
  track: number;
  top: number;
  width: number;
  sticker: DanmakuMessage["sticker"];
  imageFailed: boolean;
  startedAt: number;
  durationMs: number;
  style: Record<string, string>;
};
type PendingMessage = {
  message: DanmakuMessage;
  queuedAt: number;
};
type DanmakuEvent = {
  type?: string;
  code?: string;
  message?: DanmakuMessage;
  settings?: DanmakuSettings;
  session?: DanmakuSession;
};

const MAX_PENDING_MESSAGES = 200;
const DANMAKU_QUEUE_RETRY_MS = 50;
const DEFAULT_ENTRY_INTERVAL_SECONDS = 1;
const DEFAULT_MAX_WAIT_SECONDS = 1.5;
const DANMAKU_FONT_FAMILY = 'Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
const DANMAKU_FONT_WEIGHT = 750;
const bootstrap = ref<DanmakuOverlayBootstrap>();
const settings = ref<DanmakuSettings>();
const activeItems = ref<ActiveItem[]>([]);
const pendingMessages = ref<PendingMessage[]>([]);
const lastMessageId = ref(0);
const scheduler = createTaskScheduler();
let socket: WebSocket | undefined;
let itemSequence = 0;
let nextTrackIndex = 0;
let reconnectAttempt = 0;
let stopped = false;
let recovering = false;
let reconcilingRealtimeMessages = false;
let pendingRealtimeMessages: DanmakuMessage[] = [];
let unsubscribeOverlaySession: (() => void) | undefined;
let flushTaskId: ScheduledTaskId | undefined;
let reconnectTaskId: ScheduledTaskId | undefined;
let realtimeRetryTaskId: ScheduledTaskId | undefined;
let textMeasureContext: CanvasRenderingContext2D | undefined;
let textMeasureInitialized = false;

const canRender = computed(() => Boolean(bootstrap.value && settings.value));
const normalizeTrack = (top: number, next: DanmakuSettings) => {
  const displayHeight = Math.max(1, next.display_bottom - next.display_top);
  const track = Math.round(((top - next.display_top) / displayHeight) * next.track_count - 0.5);
  return Math.max(0, Math.min(next.track_count - 1, track));
};
const setSettings = (next: DanmakuSettings) => {
  settings.value = next;
  activeItems.value.forEach((item) => {
    item.track = normalizeTrack(item.top, next);
  });
  nextTrackIndex = next.track_count > 0 ? nextTrackIndex % next.track_count : 0;
  if (pendingMessages.value.length > 0) scheduleFlush();
};
const clearRuntime = () => {
  activeItems.value = [];
  pendingMessages.value = [];
  nextTrackIndex = 0;
};
const cancelScheduledTask = (taskId: ScheduledTaskId | undefined) => {
  if (taskId !== undefined) scheduler.cancel(taskId);
};
const stopSocket = () => {
  cancelScheduledTask(reconnectTaskId);
  cancelScheduledTask(realtimeRetryTaskId);
  reconnectTaskId = undefined;
  realtimeRetryTaskId = undefined;
  socket?.close();
  socket = undefined;
};
const resetRuntime = (next: DanmakuOverlayBootstrap) => {
  stopSocket();
  scheduler.clear();
  flushTaskId = undefined;
  stopped = false;
  recovering = false;
  reconcilingRealtimeMessages = false;
  pendingRealtimeMessages = [];
  reconnectAttempt = 0;
  bootstrap.value = next;
  lastMessageId.value = next.session.latest_message_id;
  clearRuntime();
  setSettings(next.session.settings);
  connect();
};
const scheduleFlushAfter = (delayMs: number) => {
  if (flushTaskId !== undefined || stopped) return;
  flushTaskId = scheduler.scheduleAfter(delayMs, () => {
    flushTaskId = undefined;
    flushQueue();
  });
};
const scheduleFlush = () => scheduleFlushAfter(0);
const getTextMeasureContext = () => {
  if (!textMeasureInitialized) {
    textMeasureInitialized = true;
    textMeasureContext = document.createElement("canvas").getContext("2d") ?? undefined;
  }
  return textMeasureContext;
};
const measureBodyWidth = (body: string, fontSize: number) => {
  const context = getTextMeasureContext();
  if (!context) return measureDanmakuText(body, fontSize, () => Number.NaN);
  context.font = `${DANMAKU_FONT_WEIGHT} ${fontSize}px ${DANMAKU_FONT_FAMILY}`;
  return measureDanmakuText(body, fontSize, (text) => context.measureText(text).width);
};
const measureMessageWidth = (message: DanmakuMessage, fontSize: number) => {
  if (message.message_type === "sticker" && message.sticker) {
    const imageWidth = measureDanmakuImageWidth(message.sticker.width, message.sticker.height, fontSize);
    const fallbackWidth = measureBodyWidth(message.body, fontSize);
    return Math.max(imageWidth, fallbackWidth);
  }
  return measureBodyWidth(message.body, fontSize);
};
const resolveImageURL = (imageURL: string) => {
  const apiBaseUrl = bootstrap.value?.apiBaseUrl;
  if (!apiBaseUrl) return imageURL;
  return new URL(imageURL, apiBaseUrl).toString();
};
const markImageFailed = (key: string) => {
  const item = activeItems.value.find((candidate) => candidate.key === key);
  if (item) item.imageFailed = true;
};
const queueMessage = (message: DanmakuMessage) => {
  if (!canRender.value || message.message_id <= lastMessageId.value) return;
  lastMessageId.value = message.message_id;
  if (pendingMessages.value.length >= MAX_PENDING_MESSAGES) pendingMessages.value.shift();
  pendingMessages.value.push({ message, queuedAt: performance.now() });
  scheduleFlush();
};
const flushQueue = () => {
  if (!canRender.value || pendingMessages.value.length === 0 || !settings.value) return;
  const now = performance.now();
  const currentSettings = settings.value;
  const viewportWidth = Math.max(1, document.documentElement.clientWidth || window.innerWidth);
  const maxWaitSeconds = Number.isFinite(currentSettings.max_wait_seconds)
    ? currentSettings.max_wait_seconds
    : DEFAULT_MAX_WAIT_SECONDS;
  const entryIntervalSeconds = Number.isFinite(currentSettings.entry_interval_seconds)
    ? currentSettings.entry_interval_seconds
    : DEFAULT_ENTRY_INTERVAL_SECONDS;
  const maxWaitMilliseconds = maxWaitSeconds * 1000;
  const entryIntervalMilliseconds = entryIntervalSeconds * 1000;
  while (pendingMessages.value.length > 0) {
    const pending = pendingMessages.value[0];
    if (isPendingMessageExpired(pending.queuedAt, now, maxWaitMilliseconds)) {
      pendingMessages.value.shift();
      continue;
    }
    const width = measureMessageWidth(pending.message, currentSettings.font_size);
    const stickerHeight = currentSettings.font_size * DANMAKU_STICKER_HEIGHT_MULTIPLIER;
    const durationMs = currentSettings.duration_seconds * 1000;
    const candidate: DanmakuMotion = { startedAt: now, durationMs, width };
    const track = findSafeTrack(
      activeItems.value,
      candidate,
      currentSettings.track_count,
      viewportWidth,
      nextTrackIndex,
      now,
      entryIntervalMilliseconds,
      DANMAKU_GAP_PX,
    );
    if (track < 0) {
      scheduleFlushAfter(DANMAKU_QUEUE_RETRY_MS);
      return;
    }
    pendingMessages.value.shift();
    const displayHeight = currentSettings.display_bottom - currentSettings.display_top;
    const top = currentSettings.display_top + ((track + 0.5) / currentSettings.track_count) * displayHeight;
    const key = `${pending.message.message_id}-${itemSequence++}`;
    activeItems.value.push({
      key,
      body: pending.message.body,
      track,
      top,
      width,
      sticker: pending.message.message_type === "sticker" ? pending.message.sticker : null,
      imageFailed: false,
      startedAt: now,
      durationMs,
      style: {
        "--danmaku-top": `${top}%`,
        "--danmaku-font-size": `${currentSettings.font_size}px`,
        "--danmaku-opacity": String(currentSettings.opacity),
        "--danmaku-duration": `${currentSettings.duration_seconds}s`,
        "--danmaku-width": `${width}px`,
        "--danmaku-sticker-height": `${stickerHeight}px`,
        "--danmaku-color": currentSettings.text_color,
      },
    });
    nextTrackIndex = (track + 1) % currentSettings.track_count;
    scheduler.scheduleAt(now + durationMs, () => {
      activeItems.value = activeItems.value.filter((item) => item.key !== key);
      scheduleFlush();
    });
  }
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
const drainPendingRealtimeMessages = () => {
  const drained = takeContiguousRealtimeMessages(lastMessageId.value, pendingRealtimeMessages);
  pendingRealtimeMessages = drained.remaining;
  drained.messages.forEach(queueMessage);
};
const scheduleRealtimeRetry = () => {
  if (realtimeRetryTaskId !== undefined || stopped || recovering || pendingRealtimeMessages.length === 0) return;
  realtimeRetryTaskId = scheduler.scheduleAfter(500, () => {
    realtimeRetryTaskId = undefined;
    void reconcileRealtimeMessages();
  });
};
const reconcileRealtimeMessages = async () => {
  if (reconcilingRealtimeMessages || recovering || stopped || !bootstrap.value) return;
  reconcilingRealtimeMessages = true;
  try {
    while (!stopped && pendingRealtimeMessages.length > 0) {
      drainPendingRealtimeMessages();
      if (pendingRealtimeMessages.length === 0) return;
      const messages = await fetchMessagesAfter(lastMessageId.value);
      if (messages.length > 0) applyOrderedMessages(messages);
      drainPendingRealtimeMessages();
      pendingRealtimeMessages = removeResolvedRealtimeMessages(pendingRealtimeMessages, lastMessageId.value);
      if (messages.length === 0) return;
    }
  } catch {
    // Keep complete WebSocket messages pending so a temporary HTTP failure cannot skip live messages.
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
    drainPendingRealtimeMessages();
    recoveredCompletely = true;
  } catch {
    // Keep the prior cursor so the next WebSocket session retries the complete missed range.
    ws.close(1012, "弹幕补齐失败，正在重连");
  } finally {
    recovering = false;
    if (!recoveredCompletely) return;
    drainPendingRealtimeMessages();
    pendingRealtimeMessages = removeResolvedRealtimeMessages(pendingRealtimeMessages, lastMessageId.value);
    void reconcileRealtimeMessages();
  }
};
const handleRealtimeMessage = (message: DanmakuMessage) => {
  if (bootstrap.value?.session.activity_id !== message.activity_id) return;
  pendingRealtimeMessages = removeResolvedRealtimeMessages(pendingRealtimeMessages, lastMessageId.value);
  const decision = getRealtimeMessageDecision(
    lastMessageId.value,
    message.message_id,
    recovering || reconcilingRealtimeMessages || pendingRealtimeMessages.length > 0,
  );
  if (decision === "ignore") return;
  if (decision === "direct") {
    queueMessage(message);
    return;
  }
  pendingRealtimeMessages = addPendingRealtimeMessage(pendingRealtimeMessages, message);
  drainPendingRealtimeMessages();
  if (pendingRealtimeMessages.length > 0) void reconcileRealtimeMessages();
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
      handleRealtimeMessage(payload.message);
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
    if (reconnectTaskId !== undefined) return;
    const delay = Math.min(10_000, 1_000 * 2 ** reconnectAttempt++);
    reconnectTaskId = scheduler.scheduleAfter(delay, () => {
      reconnectTaskId = undefined;
      connect();
    });
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
  scheduler.clear();
  flushTaskId = undefined;
});
</script>
