<template>
  <section class="chat-content">
    <div ref="messageList" class="chat-messages">
      <VanLoading v-if="loading" class="chat-loading" size="24px" color="var(--activity-gold)" />
      <button v-else-if="hasMore" class="chat-load-more" type="button" @click="loadOlder">加载更早消息</button>
      <p v-if="!loading && messages.length === 0" class="chat-empty">还没有消息，来打个招呼吧。</p>
      <article
        v-for="message in messages"
        :key="message.message_id"
        class="chat-message"
        :class="{ 'chat-message--self': message.sender_activity_user_id === user.activity_user_id }"
      >
        <ActivityAvatar
          :avatar-id="messageAvatarId(message)"
          variant="small"
          :alt="`${message.sender_username}的活动头像`"
        />
        <div class="chat-message-content">
          <div class="chat-message-meta">
            <strong>{{ message.sender_username }}</strong>
            <time :datetime="message.created_at">{{ formatTime(message.created_at) }}</time>
          </div>
          <p
            class="chat-message-bubble"
            :class="{ 'chat-message-bubble--sticker': message.message_type === 'sticker' }"
          >
            <template v-if="message.message_type === 'sticker' && message.sticker">
              <img
                v-if="!failedStickerMessages.has(message.message_id)"
                :src="mediaURL(message.sticker.image_url) || undefined"
                :alt="message.sticker.name"
                @error="markStickerError(message.message_id)"
              />
              <span v-else>{{ message.body }}</span>
            </template>
            <template v-else>{{ message.body }}</template>
          </p>
        </div>
      </article>
    </div>
    <form ref="composer" class="chat-composer" @submit.prevent="sendMessage">
      <div
        v-if="stickerPickerOpen"
        id="chat-sticker-panel"
        class="chat-sticker-panel"
        role="dialog"
        aria-label="表情包选择器"
      >
        <p v-if="stickersLoading" class="chat-sticker-empty">正在加载表情</p>
        <p v-else-if="stickers.length === 0" class="chat-sticker-empty">暂无表情</p>
        <template v-else>
          <button
            v-for="sticker in stickers"
            :key="sticker.sticker_id"
            class="chat-sticker-option"
            type="button"
            :disabled="!canSendSticker || sending"
            :aria-label="`发送${sticker.name}表情`"
            @click="sendSticker(sticker)"
          >
            <img
              :src="mediaURL(sticker.image_url) || undefined"
              :alt="sticker.name"
              loading="lazy"
            />
          </button>
        </template>
      </div>
      <div class="chat-composer-controls">
        <VanField
          v-model="draft"
          :disabled="activity.status !== 'open' || sending"
          maxlength="500"
          rows="1"
          :autosize="{ minHeight: 24, maxHeight: 72 }"
          type="textarea"
          placeholder="输入消息"
          @click="stickerPickerOpen = false"
          @focus="stickerPickerOpen = false"
        />
        <VanButton
          native-type="button"
          type="default"
          class="chat-sticker-toggle"
          :disabled="activity.status !== 'open' || connectionState !== 'connected' || sending || Boolean(draft.trim())"
          :aria-controls="stickerPickerOpen ? 'chat-sticker-panel' : undefined"
          :aria-expanded="stickerPickerOpen"
          aria-haspopup="dialog"
          :aria-label="stickerPickerOpen ? '关闭表情包' : '打开表情包'"
          @click="stickerPickerOpen = !stickerPickerOpen"
        >
          <img class="chat-control-icon chat-smile-icon" :src="chatSmileIcon" alt="" aria-hidden="true" />
        </VanButton>
        <VanButton
          native-type="submit"
          type="primary"
          :disabled="!canSend"
          :loading="sending"
          aria-label="发送"
          class="chat-send-button"
        >
          <img class="chat-control-icon chat-send-icon" :src="chatSendIcon" alt="" aria-hidden="true" />
        </VanButton>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { Button as VanButton, Field as VanField, Loading as VanLoading, showToast } from "vant";
import "./chat.css";
import chatSendIcon from "../../assets/icons/chat-send.svg";
import chatSmileIcon from "../../assets/icons/chat-smile.svg";
import {
  getActivityToken,
  getChatMessages,
  getChatStickers,
  chatWebSocketURL,
  mediaURL,
  type Activity,
  type ActivityAvatarId,
  type ChatSticker,
  type ActivityUserResponse,
  type ChatMessage,
} from "../../api/client";
import ActivityAvatar from "../../components/ActivityAvatar.vue";
import { activitySessionKey, type ActivitySession } from "./session";

const props = defineProps<{ activity: Activity; user: ActivityUserResponse }>();
const messages = ref<ChatMessage[]>([]);
const loading = ref(true);
const hasMore = ref(false);
const draft = ref("");
const stickers = ref<ChatSticker[]>([]);
const stickersLoading = ref(true);
const stickerPickerOpen = ref(false);
const failedStickerMessages = ref(new Set<number>());
const sending = ref(false);
const messageList = ref<HTMLElement>();
const composer = ref<HTMLElement>();
const connectionState = ref<"connecting" | "connected" | "offline">("connecting");
const socket = ref<WebSocket>();
const stopped = ref(false);
const session = inject<ActivitySession>(activitySessionKey);
let reconnectTimer: number | undefined;
let reconnectAttempt = 0;
const ACTIVITY_AVATAR_COUNT = 20;
const FALLBACK_AVATAR_ID: ActivityAvatarId = 1;

const messageAvatarId = (message: ChatMessage): ActivityAvatarId => {
  if (message.sender_activity_user_id === props.user.activity_user_id) return props.user.avatar_id;
  const senderId = message.sender_activity_user_id;
  if (!Number.isSafeInteger(senderId) || senderId < 1) return FALLBACK_AVATAR_ID;
  return ((senderId - 1) % ACTIVITY_AVATAR_COUNT + 1) as ActivityAvatarId;
};

type ChatScrollSnapshot = { scrollable: boolean; nearBottom: boolean };

const appendMessages = (incoming: ChatMessage[]) => {
  const previousIds = new Set(messages.value.map((message) => message.message_id));
  const byId = new Map(messages.value.map((message) => [message.message_id, message]));
  incoming.forEach((message) => byId.set(message.message_id, message));
  messages.value = [...byId.values()].sort((a, b) => a.message_id - b.message_id);
  return messages.value.filter((message) => !previousIds.has(message.message_id)).length;
};
const captureScrollSnapshot = (): ChatScrollSnapshot => {
  const element = messageList.value;
  if (!element) return { scrollable: false, nearBottom: false };
  const scrollable = element.scrollHeight > element.clientHeight;
  const distanceFromBottom = element.scrollHeight - element.clientHeight - element.scrollTop;
  return {
    scrollable,
    nearBottom: scrollable && distanceFromBottom <= element.clientHeight / 3,
  };
};
const scrollToLatest = (behavior: ScrollBehavior = "smooth") => {
  const element = messageList.value;
  if (!element) return;
  element.scrollTo({ top: element.scrollHeight, behavior });
};
const revealNewMessages = async (previous: ChatScrollSnapshot) => {
  await nextTick();
  const element = messageList.value;
  if (!element) return;
  const scrollable = element.scrollHeight > element.clientHeight;
  const shouldScroll = (previous.scrollable && previous.nearBottom) || (!previous.scrollable && scrollable);
  if (shouldScroll) scrollToLatest();
};
const appendRealtimeMessages = async (incoming: ChatMessage[]) => {
  const previous = captureScrollSnapshot();
  if (appendMessages(incoming) === 0) return;
  await revealNewMessages(previous);
};
const fetchMessages = async (
  params: { before_id?: number; after_id?: number } = {},
  updateHistoryState = true,
  autoScrollNewMessages = false,
) => {
  const token = getActivityToken(props.activity.activity_id);
  if (!token) return;
  const page = await getChatMessages(props.activity.activity_id, token, params);
  const previous = autoScrollNewMessages ? captureScrollSnapshot() : undefined;
  const addedCount = appendMessages(page.items);
  if (updateHistoryState) hasMore.value = page.has_more;
  if (autoScrollNewMessages && previous && addedCount > 0) await revealNewMessages(previous);
  return page;
};
const fetchReconnectMessages = async () => {
  let cursor = messages.value.at(-1)?.message_id;
  while (!stopped.value) {
    const page = await fetchMessages(cursor ? { after_id: cursor } : {}, false, true);
    if (!page || page.items.length === 0 || !page.has_more) return;
    const latest = messages.value.at(-1)?.message_id;
    if (!latest || latest === cursor) return;
    cursor = latest;
  }
};
const fetchStickers = async () => {
  const token = getActivityToken(props.activity.activity_id);
  if (!token) {
    stickersLoading.value = false;
    return;
  }
  try {
    stickers.value = await getChatStickers(props.activity.activity_id, token);
  } catch {
    stickers.value = [];
    showToast("表情包加载失败");
  } finally {
    stickersLoading.value = false;
  }
};
const loadOlder = async () => {
  const oldest = messages.value[0]?.message_id;
  if (!oldest) return;
  const list = messageList.value;
  const previousScrollHeight = list?.scrollHeight ?? 0;
  const previousScrollTop = list?.scrollTop ?? 0;
  try { await fetchMessages({ before_id: oldest }); } catch { showToast("历史消息加载失败"); }
  await nextTick();
  if (list) list.scrollTop = previousScrollTop + list.scrollHeight - previousScrollHeight;
};
const connect = () => {
  if (stopped.value) return;
  connectionState.value = "connecting";
  const token = getActivityToken(props.activity.activity_id);
  if (!token) return;
  const ws = new WebSocket(chatWebSocketURL(props.activity.activity_id));
  socket.value = ws;
  ws.onopen = () => { reconnectAttempt = 0; ws.send(JSON.stringify({ type: "auth", token })); };
  ws.onmessage = async (event) => {
    let payload: unknown;
    try { payload = JSON.parse(event.data); } catch { return; }
    if (!payload || typeof payload !== "object") return;
    const data = payload as {
      type?: string;
      code?: string;
      message?: ChatMessage;
      detail?: string;
    };
    if (data.type === "chat.ready") {
      connectionState.value = "connected";
      try { await fetchReconnectMessages(); } catch { /* 下一次重连时重试 */ }
    } else if (data.type === "message.created" && data.message) {
      await appendRealtimeMessages([data.message]);
    } else if (data.type === "chat.error" && data.detail) {
      showToast(data.detail);
      if (data.code === "unauthorized") {
        stopped.value = true;
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        session?.logout();
      }
    }
  };
  ws.onclose = () => {
    if (stopped.value) return;
    connectionState.value = "offline";
    const delay = Math.min(10000, 1000 * 2 ** reconnectAttempt++);
    reconnectTimer = window.setTimeout(connect, delay);
  };
  ws.onerror = () => ws.close();
};
const sendPayload = (payload: { body?: string; sticker_id?: number }) => {
  if (!socket.value || socket.value.readyState !== WebSocket.OPEN || props.activity.status !== "open") return false;
  sending.value = true;
  socket.value.send(JSON.stringify({ type: "message.send", ...payload }));
  window.setTimeout(() => { sending.value = false; }, 300);
  return true;
};
const sendMessage = () => {
  const body = draft.value.trim();
  if (!body || !canSend.value) return;
  if (sendPayload({ body })) draft.value = "";
};
const sendSticker = (sticker: ChatSticker) => {
  if (!canSendSticker.value) return;
  if (sendPayload({ sticker_id: sticker.sticker_id })) stickerPickerOpen.value = false;
};
const markStickerError = (messageId: number) => {
  failedStickerMessages.value = new Set(failedStickerMessages.value).add(messageId);
};
const handleDocumentPointerDown = (event: PointerEvent) => {
  if (!stickerPickerOpen.value) return;
  const target = event.target;
  if (target instanceof Node && !composer.value?.contains(target)) stickerPickerOpen.value = false;
};
const handleDocumentKeydown = (event: KeyboardEvent) => {
  if (event.key === "Escape") stickerPickerOpen.value = false;
};
const formatTime = (value: string) => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const canSend = computed(() =>
  props.activity.status === "open"
  && draft.value.trim().length > 0
  && connectionState.value === "connected"
);
const canSendSticker = computed(() =>
  props.activity.status === "open"
  && !draft.value.trim()
  && connectionState.value === "connected"
);

onMounted(async () => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleDocumentKeydown);
  await Promise.all([
    fetchMessages().catch(() => showToast("消息加载失败")),
    fetchStickers(),
  ]);
  loading.value = false;
  await nextTick();
  scrollToLatest("auto");
  connect();
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleDocumentKeydown);
  stopped.value = true;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  socket.value?.close();
});
</script>
