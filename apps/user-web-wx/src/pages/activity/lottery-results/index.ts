import {
  Activity,
  MobileLotteryAward,
  MobileLotteryDraw,
  MobileLotteryPrize,
  MobileLotteryRound,
  MobileLotterySnapshot,
} from "../../../types/api";
import { ReconnectingSocket } from "../../../services/socket";
import {
  currentActivityId,
  goToHome,
  goToEntry,
  loadActivityContext,
  resolveActivityId,
} from "../../../services/session";
import { drawsForPrize, flattenPrizes, ViewerPrize } from "../../../utils/lottery";
import { lotteryWebSocketURL, mediaURL } from "../../../utils/http";

interface ViewerPrizeData extends ViewerPrize {
  imageURL: string;
  showImage: boolean;
}

interface ResultsData {
  loading: boolean;
  error: string;
  statusBarHeight: number;
  connectionLabel: string;
  connectionClass: string;
  activityStatusLabel: string;
  activityClass: string;
  activeIndex: number;
  prizes: ViewerPrizeData[];
  currentPrize?: ViewerPrizeData;
  currentDraws: MobileLotteryDraw[];
  currentPrizeStatusLabel: string;
  currentPrizeClass: string;
  noWinnerLabel: string;
}

Page({
  data: {
    loading: true,
    error: "",
    statusBarHeight: 0,
    connectionLabel: "连接中",
    connectionClass: "",
    activityStatusLabel: "",
    activityClass: "",
    activeIndex: 0,
    prizes: [],
    currentPrize: undefined,
    currentDraws: [],
    currentPrizeStatusLabel: "待开奖",
    currentPrizeClass: "",
    noWinnerLabel: "暂未开奖",
  } as ResultsData,

  activityId: "",
  activity: undefined as Activity | undefined,
  snapshot: undefined as MobileLotterySnapshot | undefined,
  activeRound: undefined as MobileLotteryRound | undefined,
  socket: undefined as ReconnectingSocket | undefined,
  pingTimer: undefined as number | undefined,
  failedImageURLs: undefined as Set<string> | undefined,

  onLoad(options: { activity_id?: string }) {
    this.failedImageURLs = new Set<string>();
    this.activityId = resolveActivityId(options) ?? currentActivityId() ?? "";
    this.setData({ statusBarHeight: getApp<IAppOption>().globalData.statusBarHeight });
    if (!this.activityId) {
      goToEntry();
      return;
    }
    this.load();
  },

  onUnload() {
    this.stopSocket();
  },

  async load() {
    this.stopSocket();
    this.setData({ loading: true, error: "", connectionLabel: "连接中", connectionClass: "" });
    try {
      const context = await loadActivityContext(this.activityId);
      if (!context.user) {
        goToEntry();
        return;
      }
      this.activity = context.activity;
      this.connect();
    } catch (error) {
      this.setData({ loading: false, error: error instanceof Error ? error.message : "活动加载失败" });
    }
  },

  connect() {
    this.socket = new ReconnectingSocket(
      lotteryWebSocketURL(this.activityId),
      {
        onOpen: () => {
          this.setData({ connectionLabel: "实时连接", connectionClass: "tag--success" });
          this.socket?.send({ type: "lottery.ping" });
          this.startPing();
        },
        onMessage: (payload) => this.handleMessage(payload),
        onClose: () => this.setData({ connectionLabel: "重连中", connectionClass: "" }),
        onError: (message) => {
          console.error("[公开抽奖 WebSocket] 连接失败", {
            url: lotteryWebSocketURL(this.activityId),
            message,
          });
          this.setData({ connectionLabel: "连接失败，重连中", connectionClass: "" });
        },
        minDelay: 500,
        maxDelay: 8000,
      },
    );
    this.socket.start();
  },

  startPing() {
    if (this.pingTimer !== undefined) clearInterval(this.pingTimer);
    this.pingTimer = setInterval(() => this.socket?.send({ type: "lottery.ping" }), 20000) as unknown as number;
  },

  stopSocket() {
    if (this.pingTimer !== undefined) clearInterval(this.pingTimer);
    this.pingTimer = undefined;
    this.socket?.stop();
    this.socket = undefined;
  },

  handleMessage(payload: Record<string, unknown>) {
    if (payload.type === "lottery.ready") {
      this.applySnapshot(payload as unknown as MobileLotterySnapshot);
      this.setData({ loading: false, error: "", connectionLabel: "实时连接", connectionClass: "tag--success" });
      return;
    }
    if (payload.type === "lottery.config.updated" && payload.config) {
      this.applyConfigUpdate(payload.config as Record<string, unknown>);
      return;
    }
    if (payload.type === "lottery.draw.started" && payload.round) {
      this.activeRound = payload.round as MobileLotteryRound;
      this.refreshView();
      return;
    }
    if (payload.type === "lottery.draw.stopping") {
      const roundId = typeof payload.round_id === "string" ? payload.round_id : "";
      if (roundId && roundId === this.activeRound?.round_id) {
        this.activeRound = { ...this.activeRound, phase: "stopping" };
        this.refreshView();
      }
      return;
    }
    if (payload.type === "lottery.drawn" && payload.draw) {
      const draw = payload.draw as MobileLotteryDraw;
      const draws = this.snapshot?.draws ?? [];
      this.snapshot = {
        ...this.snapshot!,
        draws: [...draws.filter((item: MobileLotteryDraw) => item.draw_id !== draw.draw_id), draw],
      };
      this.activeRound = undefined;
      this.refreshView();
      return;
    }
    if (payload.type === "lottery.reset" && payload.snapshot) {
      this.applySnapshot(payload.snapshot as MobileLotterySnapshot);
      return;
    }
    if (payload.type === "lottery.draw.error" && payload.code === "unauthorized") {
      goToEntry();
      this.stopSocket();
      this.setData({ loading: false, error: String(payload.detail || "活动登录已失效") });
    }
  },

  applySnapshot(snapshot: MobileLotterySnapshot) {
    this.snapshot = snapshot;
    this.activeRound = snapshot.active_round || undefined;
    this.refreshView();
  },

  applyConfigUpdate(config: Record<string, unknown>) {
    if (!this.snapshot || !Array.isArray(config.awards) || !Array.isArray(config.prizes)) return;
    const awards = config.awards as MobileLotteryAward[];
    const prizes = config.prizes as MobileLotteryPrize[];
    this.snapshot = {
      ...this.snapshot,
      awards: awards.map((award) => ({
        ...award,
        prizes: prizes.filter((prize) => prize.award_id === award.award_id),
      })),
    };
    this.refreshView();
  },

  refreshView() {
    if (!this.snapshot) return;
    const flat = flattenPrizes(this.snapshot.awards);
    const activeIndex = flat.length ? Math.min(this.data.activeIndex, flat.length - 1) : 0;
    const prizes = flat.map((prize) => ({
      ...prize,
      imageURL: mediaURL(prize.image_url),
      showImage: Boolean(prize.image_url && !this.failedImageURLs?.has(prize.image_url)),
    }));
    const currentPrize = prizes[activeIndex];
    const currentDraws = drawsForPrize(this.snapshot.draws, currentPrize?.prize_id);
    const status = this.activeRound?.prize_id === currentPrize?.prize_id
      ? "drawing"
      : currentDraws.length ? "drawn" : "pending";
    this.setData({
      prizes,
      activeIndex,
      currentPrize,
      currentDraws,
      activityStatusLabel: statusLabels[this.snapshot.activity_status],
      activityClass: activityClass(this.snapshot.activity_status),
      currentPrizeStatusLabel: statusLabelsForPrize[status],
      currentPrizeClass: status === "drawn" ? "tag--success" : status === "drawing" ? "" : "",
      noWinnerLabel: status === "drawing" ? "开奖进行中" : "暂未开奖",
    });
  },

  handleSlideChange(event: WechatMiniprogram.SwiperChange) {
    this.setData({ activeIndex: event.detail.current });
    this.refreshView();
  },

  markImageFailed(event: WechatMiniprogram.CustomEvent<{ url: string }>) {
    const url = event.currentTarget.dataset.url as string;
    if (!url) return;
    this.failedImageURLs?.add(url);
    this.refreshView();
  },

  goHome() {
    goToHome();
  },
});

const statusLabels: Record<string, string> = { closed: "活动未开始", open: "活动进行中", ended: "活动已结束" };
const activityClass = (status: string) => status === "open"
  ? "tag--success"
  : status === "ended" ? "tag--danger" : "";
const statusLabelsForPrize: Record<string, string> = { drawing: "开奖中", drawn: "已开奖", pending: "待开奖" };
