import {
  MobileLotteryAward,
  MobileLotteryDraw,
  MobileLotteryPrize,
  MobileLotteryRound,
  MobileLotterySnapshot,
} from "../types/api";

export type ViewerPrize = MobileLotteryPrize & { award_name: string };
export type LotteryPhase = "idle" | "starting" | "rolling" | "stopping";

export interface LotteryControlState {
  activityStatus: MobileLotterySnapshot["activity_status"];
  prizes: MobileLotteryPrize[];
  selectedPrizeId?: number;
  lastDraw?: MobileLotteryDraw;
  activeRound?: MobileLotteryRound;
  pendingRoundId?: string;
  phase: LotteryPhase;
}

export const flattenPrizes = (awards: MobileLotteryAward[]): ViewerPrize[] => [...awards]
  .sort((left, right) => left.sort_order - right.sort_order || left.award_id - right.award_id)
  .flatMap((award) => [...award.prizes]
    .filter((prize) => prize.is_enabled)
    .sort((left, right) => left.sort_order - right.sort_order || left.prize_id - right.prize_id)
    .map((prize) => ({ ...prize, award_name: award.name })));

export const drawsForPrize = (draws: MobileLotteryDraw[], prizeId?: number) => {
  if (!prizeId) return [];
  return [...draws]
    .filter((draw) => draw.prize_id === prizeId)
    .sort((left, right) => left.draw_id - right.draw_id);
};

export const applySnapshotToControl = (snapshot: MobileLotterySnapshot): LotteryControlState => {
  const draws = [...snapshot.draws].sort((left, right) => right.draw_id - left.draw_id);
  const activeRound = snapshot.active_round || undefined;
  const selectedPrizeId = activeRound?.prize_id ?? snapshot.selected_prize_id ?? undefined;
  return {
    activityStatus: snapshot.activity_status,
    prizes: flattenPrizes(snapshot.awards),
    selectedPrizeId,
    lastDraw: draws[0],
    activeRound,
    pendingRoundId: activeRound?.round_id,
    phase: activeRound ? (activeRound.phase === "stopping" ? "stopping" : "rolling") : "idle",
  };
};

export const fallbackPrizeId = (prizes: MobileLotteryPrize[], current?: number) => {
  if (current && prizes.some((prize) => prize.prize_id === current)) return current;
  return prizes.find((prize) => prize.remaining_quantity > 0)?.prize_id ?? prizes[0]?.prize_id;
};
