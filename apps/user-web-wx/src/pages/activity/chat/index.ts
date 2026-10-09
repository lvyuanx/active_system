import { chatWebSocketURL, mediaURL } from "../../../utils/http";
import { getChatMessages, getChatStickers } from "../../../services/api";
import { Activity, ActivityAvatarId, ActivityUserResponse, ChatMessage, ChatSticker } from "../../../types/api";
import { ReconnectingSocket } from "../../../services/socket";
import {
  currentActivityId,
  goToEntry,
  loadActivityContext,
  resetActivitySession,
  resolveActivityId,
  setActivityTab,
} from "../../../services/session";
import { getActivityToken } from "../../../utils/storage";
import { mergeChatMessages, messageAvatarId } from "../../../utils/chat";

interface MessageView extends ChatMessage {
  avatarId: ActivityAvatarId;
  self: boolean;
  time: string;
  stickerImageURL: string;
  showStickerImage: boolean;
}

interface StickerView extends ChatSticker {
  imageURL: string;
}

interface ChatData {
  loading: boolean;
  error: string;
  statusBarHeight: number;
  activityStatus: Activity["status"];
  messages: MessageView[];
  hasMore: boolean;
  draft: string;
  stickers: StickerView[];
  stickersLoading: boolean;
  stickerPickerOpen: boolean;
  sending: boolean;
  connectionState: "connecting" | "connected" | "offline";
  connectionLabel: string;
  keyboardVisible: boolean;
  chatLayoutStyle: string;
  scrollIntoView: string;
  canSend: boolean;
  canSendSticker: boolean;
}

type PersistentTabBar = {
  setData(data: { hidden: boolean }): void;
};

Page({
  data: {
    loading: true,
    error: "",
    statusBarHeight: 0,
    activityStatus: "closed",
    messages: [],
    hasMore: false,
    draft: "",
    stickers: [],
    stickersLoading: true,
    stickerPickerOpen: false,
    sending: false,
    connectionState: "connecting",
    connectionLabel: "连接中",
    keyboardVisible: false,
    chatLayoutStyle: "padding-bottom: 0px;",
    scrollIntoView: "",
    canSend: false,
    canSendSticker: false,
  } as ChatData,

  activityId: "",
  activity: undefined as Activity | undefined,
  user: undefined as ActivityUserResponse | undefined,
  rawMessages: [] as ChatMessage[],
  failedStickerMessages: undefined as Set<number> | undefined,
  socket: undefined as ReconnectingSocket | undefined,
  stopped: false,
  chatLayoutStyle: "",
  nearBottom: true,
  keyboardHeightHandler: undefined as ((result: { height: number }) => void) | undefined,

  setTabBarHidden(hidden: boolean) {
    const page = this as unknown as { getTabBar?: () => PersistentTabBar | undefined };
    page.getTabBar?.()?.setData({ hidden });
  },

  onLoad(options: { activity_id?: string }) {
    this.failedStickerMessages = new Set<number>();
    this.activityId = resolveActivityId(options) ?? currentActivityId() ?? "";
    this.setTabBarHidden(false);
    const metrics = getApp<IAppOption>().globalData;
    const windowInfo = wx.getWindowInfo?.() ?? wx.getSystemInfoSync();
    const windowWidth = Number(windowInfo.windowWidth || 375);
    const tabbarReserve = Math.ceil((116 * windowWidth) / 750) + metrics.safeAreaBottom;
    this.chatLayoutStyle = `padding-bottom: ${tabbarReserve}px;`;
    this.setData({ statusBarHeight: metrics.statusBarHeight, chatLayoutStyle: this.chatLayoutStyle });
    if (!this.activityId) {
      goToEntry();
      return;
    }
    this.load();
  },

  onShow() {
    setActivityTab(1);
    this.setTabBarHidden(false);
    if (this.activityId && !this.data.loading) this.load();
  },

  onHide() {
    this.setTabBarHidden(false);
  },

  onUnload() {
    this.stopped = true;
    this.setTabBarHidden(false);
    this.socket?.stop();
    if (this.keyboardHeightHandler && wx.offKeyboardHeightChange) {
      wx.offKeyboardHeightChange(this.keyboardHeightHandler);
    }
  },

  async load() {
    this.stopped = false;
    this.socket?.stop();
    this.failedStickerMessages = new Set<number>();
    this.setData({
      loading: true,
      error: "",
      messages: [],
      hasMore: false,
      connectionState: "connecting",
      connectionLabel: "连接中",
    });
    try {
      const context = await loadActivityContext(this.activityId);
      if (!context.user) {
        goToEntry();
        return;
      }
      this.activity = context.activity;
      this.user = context.user;
      this.rawMessages = [];
      const [messagePage, stickers] = await Promise.all([
        this.fetchMessages(),
        this.fetchStickers(),
      ]);
      this.setData({
        loading: false,
        activityStatus: context.activity.status,
        hasMore: messagePage?.has_more ?? false,
        stickers,
        stickersLoading: false,
      });
      this.refreshMessageViews();
      this.scrollToLatest();
      this.connect();
      this.registerKeyboardListener();
    } catch (error) {
      this.setData({ loading: false, error: error instanceof Error ? error.message : "聊天室加载失败" });
    }
  },

  async fetchMessages(params: { before_id?: number; after_id?: number } = {}) {
    const token = getActivityToken(this.activityId);
    if (!token) return undefined;
    const page = await getChatMessages(this.activityId, token, params);
    this.mergeMessages(page.items);
    return page;
  },

  async fetchStickers() {
    const token = getActivityToken(this.activityId);
    if (!token) return [];
    try {
      const stickers = await getChatStickers(this.activityId, token);
      return stickers.map((sticker) => ({ ...sticker, imageURL: mediaURL(sticker.image_url) }));
    } catch {
      wx.showToast({ title: "表情包加载失败", icon: "none" });
      return [];
    }
  },

  mergeMessages(incoming: ChatMessage[]) {
    this.rawMessages = mergeChatMessages(this.rawMessages as ChatMessage[], incoming);
    this.refreshMessageViews();
  },

  refreshMessageViews() {
    const userId = this.user?.activity_user_id;
    const userAvatar = this.user?.avatar_id ?? 1;
    const messages = (this.rawMessages as ChatMessage[]).map((message: ChatMessage) => {
      const self = message.sender_activity_user_id === userId;
      const avatarId = messageAvatarId(message, userId, userAvatar);
      return {
        ...message,
        avatarId,
        self,
        time: formatTime(message.created_at),
        stickerImageURL: mediaURL(message.sticker?.image_url ?? null),
        showStickerImage: message.message_type === "sticker"
          && Boolean(message.sticker)
          && !this.failedStickerMessages?.has(message.message_id),
      };
    });
    this.setData({ messages, canSend: this.canSend(), canSendSticker: this.canSendSticker() });
  },

  async loadOlder() {
    const oldest = this.rawMessages[0]?.message_id;
    if (!oldest || !this.data.hasMore) return;
    try {
      const page = await this.fetchMessages({ before_id: oldest });
      this.setData({ hasMore: Boolean(page?.has_more) });
      this.setData({ scrollIntoView: `message-${oldest}` });
    } catch {
      wx.showToast({ title: "历史消息加载失败", icon: "none" });
    }
  },

  connect() {
    const token = getActivityToken(this.activityId);
    if (!token) {
      goToEntry();
      return;
    }
    this.socket = new ReconnectingSocket(chatWebSocketURL(this.activityId), {
      onOpen: () => {
        this.setData({ connectionState: "connected", connectionLabel: "已连接" });
        this.socket?.send({ type: "auth", token });
      },
      onMessage: (payload) => this.handleSocketMessage(payload),
      onClose: () => this.setData({ connectionState: "offline", connectionLabel: "重连中" }),
      onError: (message) => {
        console.error("[聊天 WebSocket] 连接失败", { url: chatWebSocketURL(this.activityId), message });
        this.setData({ connectionState: "offline", connectionLabel: "连接失败，重连中" });
      },
      minDelay: 1000,
      maxDelay: 10000,
    });
    this.socket.start();
  },

  async handleSocketMessage(payload: Record<string, unknown>) {
    if (payload.type === "chat.ready") {
      this.setData({ connectionState: "connected", connectionLabel: "已连接" });
      await this.fetchReconnectMessages();
      return;
    }
    if (payload.type === "message.created" && payload.message) {
      const wasNearBottom = this.nearBottom;
      this.mergeMessages([payload.message as ChatMessage]);
      if (wasNearBottom) this.scrollToLatest();
      return;
    }
    if (payload.type === "chat.error") {
      const code = String(payload.code || "");
      const detail = String(payload.detail || "聊天服务暂时不可用");
      if (code === "unauthorized") {
        resetActivitySession(this.activityId);
        this.socket?.stop();
        goToEntry();
      } else {
        wx.showToast({ title: detail, icon: "none" });
      }
    }
  },

  async fetchReconnectMessages() {
    let cursor = this.rawMessages[this.rawMessages.length - 1]?.message_id;
    while (!this.stopped) {
      const page = await this.fetchMessages(cursor ? { after_id: cursor } : {});
      if (!page || page.items.length === 0 || !page.has_more) return;
      const latest = this.rawMessages[this.rawMessages.length - 1]?.message_id;
      if (!latest || latest === cursor) return;
      cursor = latest;
    }
  },

  handleDraftInput(event: WechatMiniprogram.Input) {
    this.setData({ draft: event.detail.value, stickerPickerOpen: false });
    this.refreshMessageViews();
  },

  handleInputFocus() {
    this.setData({ stickerPickerOpen: false });
    this.scrollToLatest();
  },

  toggleStickerPicker() {
    if (!this.canSendSticker()) return;
    this.setData({ stickerPickerOpen: !this.data.stickerPickerOpen });
    if (this.data.stickerPickerOpen) this.scrollToLatest();
  },

  stopPickerPropagation() {
    return false;
  },

  closePicker() {
    if (this.data.stickerPickerOpen) this.setData({ stickerPickerOpen: false });
  },

  sendMessage() {
    const body = this.data.draft.trim();
    if (!body || !this.canSend()) return;
    if (this.sendPayload({ body })) this.setData({ draft: "" });
  },

  sendSticker(event: WechatMiniprogram.CustomEvent) {
    const stickerId = Number(event.currentTarget.dataset.id);
    if (!this.canSendSticker()) return;
    if (this.sendPayload({ sticker_id: stickerId })) this.setData({ stickerPickerOpen: false });
  },

  sendPayload(payload: { body?: string; sticker_id?: number }) {
    if (this.data.activityStatus !== "open" || this.data.connectionState !== "connected") return false;
    if (!this.socket?.send({ type: "message.send", ...payload })) return false;
    this.setData({ sending: true });
    setTimeout(() => this.setData({ sending: false }), 300);
    return true;
  },

  canSend() {
    return this.data.activityStatus === "open"
      && this.data.connectionState === "connected"
      && Boolean(this.data.draft.trim());
  },

  canSendSticker() {
    return this.data.activityStatus === "open"
      && this.data.connectionState === "connected"
      && !this.data.draft.trim();
  },

  markStickerError(event: WechatMiniprogram.CustomEvent) {
    const messageId = Number(event.currentTarget.dataset.id);
    this.failedStickerMessages?.add(messageId);
    this.refreshMessageViews();
  },

  handleScroll(event: WechatMiniprogram.ScrollViewScroll) {
    const detail = event.detail as { scrollTop?: number; scrollHeight?: number; deltaY?: number };
    if (typeof detail.scrollHeight === "number" && typeof detail.scrollTop === "number") {
      this.nearBottom = detail.scrollHeight - detail.scrollTop <= 180;
    } else if (typeof detail.deltaY === "number") {
      if (detail.deltaY < 0) this.nearBottom = false;
    }
  },

  scrollToLatest() {
    this.nearBottom = true;
    this.setData({ scrollIntoView: "chat-bottom" });
    setTimeout(() => this.setData({ scrollIntoView: "" }), 80);
  },

  registerKeyboardListener() {
    this.keyboardHeightHandler = ({ height }: { height: number }) => {
      const visible = height > 0;
      this.setTabBarHidden(visible);
      this.setData({
        keyboardVisible: visible,
        chatLayoutStyle: visible ? "padding-bottom: 0px;" : this.chatLayoutStyle,
      });
      if (visible) this.scrollToLatest();
    };
    wx.onKeyboardHeightChange?.(this.keyboardHeightHandler);
  },
});

const formatTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
};
