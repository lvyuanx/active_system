export interface LotteryQueueDraw {
  draw_id: number;
}

export function enqueueLotteryDraw<T extends LotteryQueueDraw>(
  knownDrawIds: Set<number>,
  queue: T[],
  draw: T,
): T[] {
  if (knownDrawIds.has(draw.draw_id) || queue.some((item) => item.draw_id === draw.draw_id)) {
    return queue;
  }
  knownDrawIds.add(draw.draw_id);
  return [...queue, draw].sort((left, right) => left.draw_id - right.draw_id);
}

export function readyLotteryDrawIds(draws: LotteryQueueDraw[]): Set<number> {
  return new Set(draws.map((draw) => draw.draw_id));
}
