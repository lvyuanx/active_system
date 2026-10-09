import { mobileLotteryWebSocketURL, mediaURL } from "../../../utils/http";
import {
  Activity,
  ActivityUserResponse,
  MobileLotteryDraw,
  MobileLotteryPrize,
  MobileLotterySnapshot,
} from "../../../types/api";
import { ReconnectingSocket } from "../../../services/socket";
import {
  currentActivityId,
  goToEntry,
  goToHome,
  loadActivityContext,
  resetActivitySession,
  resolveActivityId,
} from "../../../services/session";
import { applySnapshotToControl, fallbackPrizeId, LotteryControlState } from "../../../utils/lottery";
import { getActivityToken } from "../../../utils/storage";

interface ControlPrize extends MobileLotteryPrize {
  imageURL: string;
  showImage: boolean;
  selected: boolean;
  selectable: boolean;
  className: string;
}

interface LotteryData {
  loading: boolean;
  error: string;
  actionError: string;
  statusBarHeight: number;
  connectionLabel: string;
  connectionClass: string;
  activityStatusLabel: string;
  activityClass: string;
  prizes: ControlPrize[];
  selectedPrizeId?: number;
  selectedPrizeName: string;
  phase: LotteryControlState["phase"];
  drawButtonLabel: string;
  drawHint: string;
  controlDisabled: boolean;
  lastDraw: MobileLotteryDraw | null;
}

Page({
  data: {
    loading: true,
    error: "",
    actionError: "",
    statusBarHeight: 0,
    connectionLabel: "连接中",
    connectionClass: "",
    activityStatusLabel: "",
    activityClass: "",
    prizes: [],
    selectedPrizeId: undefined,
    selectedPrizeName: "",
    phase: "idle",
    drawButtonLabel: "开始抽奖",
    drawHint: "点击开始后，大屏会同步滚动抽奖。",
    controlDisabled: true,
    lastDraw: null,
  } as LotteryData,

  activityId: "",
  user: undefined as ActivityUserResponse | undefined,
  activity: undefined as Activity | undefined,
  state: undefined as LotteryControlState | undefined,
  socket: undefined as ReconnectingSocket | undefined,

  onLoad(options: { activity_id?: string }) {
    this.activityId = resolveActivityId(options) ?? currentActivityId() ?? "";
    this.setData({ statusBarHeight: getApp<IAppOption>().globalData.statusBarHeight });
    if (!this.activityId) {
      goToEntry();
      return;
    }
    this.load();
  },

  onUnload() {
    this.socket?.stop();
  },

  async load() {
    this.socket?.stop();
    this.setData({ loading: true, error: "", actionError: "", connectionLabel: "连接中", connectionClass: "" });
    try {
      const context = await loadActivityContext(this.activityId);
      if (!context.user) {
        goToEntry();
        return;
      }
      if (!context.user.can_mobile_lottery) {
        this.setData({ loading: false, error: "你没有移动端抽奖权限" });
        return;
      }
      this.user = context.user;
      this.activity = context.activity;
      this.connect();
    } catch (error) {
      this.setData({ loading: false, error: error instanceof Error ? error.message : "活动加载失败" });
    }
  },

  connect() {
    const token = getActivityToken(this.activityId);
    if (!token) {
      goToEntry();
      return;
    }
    this.socket = new ReconnectingSocket(mobileLotteryWebSocketURL(this.activityId), {
      onOpen: () => {
        this.setData({ connectionLabel: "已连接", connectionClass: "tag--success" });
        this.socket?.send({ type: "auth", token });
      },
      onMessage: (payload) => this.handleMessage(payload),
      onClose: () => this.setData({ connectionLabel: "重连中", connectionClass: "" }),
      onError: (message) => {
        console.error("[移动端抽奖 WebSocket] 连接失败", {
          url: mobileLotteryWebSocketURL(this.activityId),
          message,
        });
        this.setData({ connectionLabel: "连接失败，重连中", connectionClass: "" });
      },
      minDelay: 500,
      maxDelay: 8000,
    });
    this.socket.start();
  },

  handleMessage(payload: Record<string, unknown>) {
    if (payload.type === "lottery.ready") {
      this.applySnapshot(payload as unknown as MobileLotterySnapshot);
      this.setData({ loading: false, error: "", connectionLabel: "已连接", connectionClass: "tag--success" });
      return;
    }
    if (payload.type === "lottery.prize.selected") {
      const id = typeof payload.selected_prize_id === "number" ? payload.selected_prize_id : undefined;
      if (id && this.state) this.state = { ...this.state, selectedPrizeId: id };
      if (id) this.setData({ selectedPrizeId: id, actionError: "" });
      this.refreshDerived();
      return;
    }
    if (payload.type === "lottery.draw.started" && payload.round) {
      this.applyRound(payload.round as LotteryControlState["activeRound"]);
      return;
    }
    if (payload.type === "lottery.draw.stopping") {
      const roundId = typeof payload.round_id === "string" ? payload.round_id : "";
      if (roundId && roundId === this.state?.pendingRoundId) {
        this.state = { ...this.state!, phase: "stopping" };
        this.refreshDerived();
      }
      return;
    }
    if (payload.type === "lottery.drawn" && payload.draw) {
      this.applyDraw(payload.draw as MobileLotteryDraw);
      return;
    }
    if (payload.type === "lottery.config.updated" && payload.config) {
      const config = payload.config as { prizes?: MobileLotteryPrize[] };
      if (Array.isArray(config.prizes)) {
        this.state = { ...this.state!, prizes: config.prizes.filter((prize) => prize.is_enabled) };
        this.refreshDerived();
      }
      return;
    }
    if (payload.type === "lottery.reset" && payload.snapshot) {
      this.applySnapshot(payload.snapshot as MobileLotterySnapshot);
      this.setData({ lastDraw: null, actionError: "" });
      return;
    }
    if (payload.type === "lottery.draw.error") {
      const detail = String(payload.detail || "抽奖失败");
      this.setData({ actionError: detail });
      if (payload.code === "unauthorized") {
        resetActivitySession(this.activityId);
        this.socket?.stop();
        goToEntry();
      } else {
        this.state = this.state
          ? { ...this.state, phase: "idle", activeRound: undefined, pendingRoundId: undefined }
          : this.state;
        this.refreshDerived();
      }
    }
  },

  applySnapshot(snapshot: MobileLotterySnapshot) {
    this.state = applySnapshotToControl(snapshot);
    this.refreshDerived();
  },

  applyRound(round: LotteryControlState["activeRound"]) {
    if (!round || !this.state) return;
    this.state = {
      ...this.state,
      activeRound: round,
      pendingRoundId: round.round_id,
      selectedPrizeId: round.prize_id,
      phase: round.phase === "stopping" ? "stopping" : "rolling",
    };
    this.refreshDerived();
  },

  applyDraw(draw: MobileLotteryDraw) {
    const state = this.state as LotteryControlState | undefined;
    if (!state) return;
    this.state = {
      ...state,
      prizes: state.prizes.map((prize: MobileLotteryPrize) => prize.prize_id === draw.prize_id
        ? { ...prize, remaining_quantity: draw.remaining_quantity }
        : prize),
      activeRound: undefined,
      pendingRoundId: undefined,
      phase: "idle",
      selectedPrizeId: draw.prize_id,
      lastDraw: draw,
    };
    this.refreshDerived();
  },

  refreshDerived() {
    const state = this.state as LotteryControlState | undefined;
    if (!state) return;
    const selectedPrizeId = fallbackPrizeId(state.prizes, state.selectedPrizeId);
    this.state = { ...state, selectedPrizeId };
    const selected = state.prizes.find((prize: MobileLotteryPrize) => prize.prize_id === selectedPrizeId);
    const phase = state.phase;
    const prizes = state.prizes.map((prize: MobileLotteryPrize) => ({
      ...prize,
      imageURL: mediaURL(prize.image_url),
      showImage: Boolean(prize.image_url),
      selected: prize.prize_id === selectedPrizeId,
      selectable: phase === "idle" && prize.remaining_quantity > 0,
      className: `control-prize ${prize.prize_id === selectedPrizeId ? "control-prize--selected" : ""} ${
        phase === "idle" && prize.remaining_quantity > 0 ? "" : "control-prize--disabled"
      }`,
    }));
    const activityStatus = this.state.activityStatus;
    this.setData({
      prizes,
      selectedPrizeId,
      selectedPrizeName: selected?.name ?? "",
      phase,
      drawButtonLabel: ({
        idle: "开始抽奖",
        starting: "准备抽奖",
        rolling: "结束抽奖",
        stopping: "开奖中",
      } as Record<string, string>)[phase],
      drawHint: getDrawHint(phase, selected, activityStatus),
      controlDisabled: this.data.connectionLabel !== "已连接"
        || !selected
        || activityStatus !== "open"
        || phase === "starting"
        || phase === "stopping"
        || (phase === "idle" && selected.remaining_quantity <= 0),
      activityStatusLabel: statusLabels[activityStatus],
      activityClass: activityClass(activityStatus),
      lastDraw: state.lastDraw,
    });
  },

  selectPrize(event: WechatMiniprogram.CustomEvent) {
    const prizeId = Number(event.currentTarget.dataset.id);
    const state = this.state as LotteryControlState | undefined;
    const selected = state?.prizes.find((prize: MobileLotteryPrize) => prize.prize_id === prizeId);
    if (!selected || state?.phase !== "idle" || selected.remaining_quantity <= 0) return;
    if (!this.socket?.send({ type: "lottery.prize.select", prize_id: prizeId })) {
      this.setData({ actionError: "抽奖连接尚未就绪，请稍候。" });
      return;
    }
    this.state = { ...state!, selectedPrizeId: prizeId };
    this.setData({ selectedPrizeId: prizeId, actionError: "" });
    this.refreshDerived();
  },

  toggleDraw() {
    if (this.data.controlDisabled) return;
    const state = this.state as LotteryControlState | undefined;
    if (!state || !this.socket) return;
    const selected = state.prizes.find((prize: MobileLotteryPrize) => prize.prize_id === state.selectedPrizeId);
    if (state.phase === "rolling" && state.activeRound) {
      if (this.socket.send({
        type: "lottery.draw.stop",
        prize_id: state.activeRound.prize_id,
        round_id: state.activeRound.round_id,
      })) {
        this.state = { ...state, phase: "stopping" };
        this.refreshDerived();
      }
      return;
    }
    if (state.phase !== "idle" || !selected || selected.remaining_quantity <= 0) return;
    const roundId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    if (this.socket.send({ type: "lottery.draw.start", prize_id: selected.prize_id, round_id: roundId })) {
      this.state = { ...state, pendingRoundId: roundId, phase: "starting" };
      this.refreshDerived();
    }
  },

  goHome() {
    goToHome();
  },
});

const statusLabels: Record<string, string> = { closed: "活动未开始", open: "活动进行中", ended: "活动已结束" };
const activityClass = (status: string) => status === "open"
  ? "tag--success"
  : status === "ended" ? "tag--danger" : "";
const getDrawHint = (phase: string, prize: MobileLotteryPrize | undefined, status: string) => {
  if (phase === "starting") return "正在通知大屏开始滚动。";
  if (phase === "rolling") return "大屏正在滚动，确认后点击结束抽奖。";
  if (phase === "stopping") return "大屏已停止滚动，正在揭晓中奖者。";
  if (prize && prize.remaining_quantity <= 0) return "当前奖品库存已用完，请切换其他奖品。";
  if (status !== "open") return "活动开启后才能发起抽奖。";
  return "点击开始后，大屏会同步滚动抽奖。";
};
