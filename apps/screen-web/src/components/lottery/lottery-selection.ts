export interface LotterySelectionDraw {
  draw_id: number;
  prize_id: number;
}

export function latestLotteryDrawForPrize<T extends LotterySelectionDraw>(
  draws: readonly T[],
  prizeId: number | undefined,
): T | undefined {
  if (!prizeId) return undefined;
  return draws.reduce<T | undefined>((latest, draw) => {
    if (draw.prize_id !== prizeId) return latest;
    return !latest || draw.draw_id > latest.draw_id ? draw : latest;
  }, undefined);
}
