import { computed, ref, type Ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type {
  Activity,
  LotteryDraw,
  LotteryRound,
  LotterySnapshot,
} from "../../api/client";

type DrawPhase = "idle" | "starting" | "rolling" | "stopping";
type SendMessage = (payload: Record<string, unknown>) => boolean;

interface LotteryRoundControlOptions {
  activity: Ref<Activity | undefined>;
  connected: Ref<boolean>;
  selectedPrizeId: Ref<number | undefined>;
  send: SendMessage;
  applySnapshot: (snapshot: LotterySnapshot) => void;
  upsertHistory: (draw: LotteryDraw) => void;
}

export function useLotteryRoundControl(options: LotteryRoundControlOptions) {
  const phase = ref<DrawPhase>("idle");
  const activeRound = ref<LotteryRound | null>(null);
  const pendingRoundId = ref<string>();
  const resetBusy = ref(false);
  const drawBusy = computed(() => phase.value !== "idle");
  const roundLocked = computed(() => phase.value !== "idle");
  const drawButtonLabel = computed(() => ({
    idle: "开始抽奖",
    starting: "准备抽奖",
    rolling: "停止抽奖",
    stopping: "开奖中",
  }[phase.value]));
  const drawButtonDisabled = computed(() => (
    !options.connected.value
    || !options.selectedPrizeId.value
    || phase.value === "starting"
    || phase.value === "stopping"
    || options.activity.value?.status !== "open"
  ));

  const createRoundId = () => globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  const startDraw = () => {
    if (phase.value !== "idle" || !options.selectedPrizeId.value) return;
    const roundId = createRoundId();
    if (!options.send({
      type: "lottery.draw.start",
      prize_id: options.selectedPrizeId.value,
      round_id: roundId,
    })) return;
    pendingRoundId.value = roundId;
    phase.value = "starting";
  };

  const stopDraw = () => {
    if (phase.value !== "rolling" || !activeRound.value) return;
    if (!options.send({
      type: "lottery.draw.stop",
      prize_id: activeRound.value.prize_id,
      round_id: activeRound.value.round_id,
    })) return;
    phase.value = "stopping";
  };

  const toggleDraw = () => {
    if (phase.value === "rolling") stopDraw();
    else startDraw();
  };

  const resetLottery = async () => {
    if (roundLocked.value || resetBusy.value) return;
    try {
      await ElMessageBox.confirm(
        "重置后所有中奖记录会清空，且大屏会同步清除中奖名单。",
        "确认重置抽奖",
        {
          confirmButtonText: "确认重置",
          cancelButtonText: "取消",
          type: "warning",
        },
      );
    } catch {
      return;
    }
    if (!options.send({ type: "lottery.reset.request" })) return;
    resetBusy.value = true;
  };

  const handleLotteryMessage = (payload: Record<string, unknown>): boolean => {
    if (payload.type === "lottery.ready") {
      const ready = payload as unknown as LotterySnapshot;
      options.applySnapshot(ready);
      activeRound.value = ready.active_round || null;
      if (activeRound.value) options.selectedPrizeId.value = activeRound.value.prize_id;
      pendingRoundId.value = activeRound.value?.round_id;
      phase.value = activeRound.value?.phase === "stopping" ? "stopping" : activeRound.value ? "rolling" : "idle";
      resetBusy.value = false;
      return true;
    }
    if (payload.type === "lottery.draw.started" && payload.round) {
      const round = payload.round as LotteryRound;
      activeRound.value = round;
      pendingRoundId.value = round.round_id;
      options.selectedPrizeId.value = round.prize_id;
      phase.value = round.phase === "stopping" ? "stopping" : "rolling";
      return true;
    }
    if (payload.type === "lottery.draw.stopping") {
      const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
      if (roundId && (roundId === pendingRoundId.value || roundId === activeRound.value?.round_id)) {
        if (activeRound.value?.round_id === roundId) {
          activeRound.value = { ...activeRound.value, phase: "stopping" };
        }
        phase.value = "stopping";
      }
      return true;
    }
    if (payload.type === "lottery.draw.result" && payload.draw) {
      options.upsertHistory(payload.draw as LotteryDraw);
      const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
      if (!roundId || roundId === pendingRoundId.value || roundId === activeRound.value?.round_id) {
        activeRound.value = null;
        pendingRoundId.value = undefined;
        phase.value = "idle";
      }
      return true;
    }
    if (payload.type === "lottery.draw.error") {
      const roundId = typeof payload.round_id === "string" ? payload.round_id : undefined;
      if (
        roundId
        && phase.value !== "idle"
        && (roundId === pendingRoundId.value || roundId === activeRound.value?.round_id)
      ) {
        activeRound.value = null;
        pendingRoundId.value = undefined;
        phase.value = "idle";
      }
      resetBusy.value = false;
      ElMessage.error(String(payload.detail || "开奖失败"));
      if (payload.code === "unauthorized") window.dispatchEvent(new CustomEvent("admin-unauthorized"));
      return true;
    }
    if (payload.type === "lottery.reset" && payload.snapshot) {
      options.applySnapshot(payload.snapshot as LotterySnapshot);
      activeRound.value = null;
      pendingRoundId.value = undefined;
      phase.value = "idle";
      resetBusy.value = false;
      ElMessage.success("中奖记录已重置");
      return true;
    }
    return payload.type !== "lottery.config.updated";
  };

  return {
    drawBusy,
    roundLocked,
    resetBusy,
    drawButtonLabel,
    drawButtonDisabled,
    toggleDraw,
    resetLottery,
    handleLotteryMessage,
  };
}
