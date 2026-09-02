export const DANMAKU_GAP_PX = 8;
export const DANMAKU_STICKER_HEIGHT_MULTIPLIER = 2.2;

export type DanmakuMotion = {
  startedAt: number;
  durationMs: number;
  width: number;
};

export type TrackDanmakuMotion = DanmakuMotion & {
  track: number;
};

export type DanmakuBounds = {
  left: number;
  right: number;
};

export type TextWidthMeasurer = (text: string) => number;

const MIN_DURATION_MS = 1;
const MIN_TEXT_WIDTH_PX = 1;
const MAX_IMAGE_WIDTH_MULTIPLIER = 6;

const finiteOr = (value: number, fallback: number) => (Number.isFinite(value) ? value : fallback);

export function measureDanmakuText(text: string, fontSize: number, measure: TextWidthMeasurer): number {
  const fallback = Math.max(MIN_TEXT_WIDTH_PX, text.length * Math.max(1, fontSize) * 0.75);
  const measured = measure(text);
  return Number.isFinite(measured) && measured > 0 ? measured : fallback;
}

export function measureDanmakuImageWidth(width: number, height: number, fontSize: number): number {
  const safeFontSize = Math.max(MIN_TEXT_WIDTH_PX, finiteOr(fontSize, MIN_TEXT_WIDTH_PX));
  const stickerHeight = safeFontSize * DANMAKU_STICKER_HEIGHT_MULTIPLIER;
  const safeWidth = finiteOr(width, 0);
  const safeHeight = finiteOr(height, 0);
  if (safeWidth <= 0 || safeHeight <= 0) return stickerHeight * MAX_IMAGE_WIDTH_MULTIPLIER;
  const proportionalWidth = stickerHeight * (safeWidth / safeHeight);
  return Math.max(
    MIN_TEXT_WIDTH_PX,
    Math.min(stickerHeight * MAX_IMAGE_WIDTH_MULTIPLIER, proportionalWidth),
  );
}

export function isPendingMessageExpired(queuedAt: number, now: number, maxWaitMs: number): boolean {
  return !Number.isFinite(queuedAt)
    || !Number.isFinite(now)
    || !Number.isFinite(maxWaitMs)
    || maxWaitMs < 0
    || now - queuedAt >= maxWaitMs;
}

export function getDanmakuBounds(
  motion: DanmakuMotion,
  at: number,
  viewportWidth: number,
): DanmakuBounds {
  const width = Math.max(MIN_TEXT_WIDTH_PX, finiteOr(motion.width, MIN_TEXT_WIDTH_PX));
  const duration = Math.max(MIN_DURATION_MS, finiteOr(motion.durationMs, MIN_DURATION_MS));
  const start = finiteOr(motion.startedAt, 0);
  const progress = Math.min(1, Math.max(0, (at - start) / duration));
  const safeViewportWidth = Math.max(MIN_TEXT_WIDTH_PX, finiteOr(viewportWidth, MIN_TEXT_WIDTH_PX));
  const left = safeViewportWidth - (safeViewportWidth + width) * progress;
  return { left, right: left + width };
}

export function getDanmakuFullyEnteredAt(motion: DanmakuMotion, viewportWidth: number): number {
  if (
    !Number.isFinite(motion.startedAt)
    || !Number.isFinite(motion.durationMs)
    || motion.durationMs <= 0
    || !Number.isFinite(motion.width)
    || motion.width <= 0
    || !Number.isFinite(viewportWidth)
    || viewportWidth <= 0
  ) {
    return Number.POSITIVE_INFINITY;
  }
  const safeWidth = Math.max(MIN_TEXT_WIDTH_PX, motion.width);
  const safeViewportWidth = Math.max(MIN_TEXT_WIDTH_PX, viewportWidth);
  return motion.startedAt + (motion.durationMs * safeWidth) / (safeViewportWidth + safeWidth);
}

export function getDanmakuEntryReadyAt(
  motion: DanmakuMotion,
  viewportWidth: number,
  entryIntervalMs: number,
): number {
  const fullyEnteredAt = getDanmakuFullyEnteredAt(motion, viewportWidth);
  if (!Number.isFinite(fullyEnteredAt)) return Number.POSITIVE_INFINITY;
  return fullyEnteredAt + Math.max(0, finiteOr(entryIntervalMs, 0));
}

const isVisible = (bounds: DanmakuBounds, viewportWidth: number) =>
  bounds.right > 0 && bounds.left < viewportWidth;

const overlapsWithGap = (
  first: DanmakuBounds,
  second: DanmakuBounds,
  gap: number,
) => first.left < second.right + gap && first.right + gap > second.left;

const collisionAt = (
  existing: DanmakuMotion,
  candidate: DanmakuMotion,
  at: number,
  viewportWidth: number,
  gap: number,
) => {
  const existingBounds = getDanmakuBounds(existing, at, viewportWidth);
  const candidateBounds = getDanmakuBounds(candidate, at, viewportWidth);
  return isVisible(existingBounds, viewportWidth)
    && isVisible(candidateBounds, viewportWidth)
    && overlapsWithGap(existingBounds, candidateBounds, gap);
};

const addRootBetween = (roots: number[], start: number, end: number, startValue: number, endValue: number) => {
  if (startValue === endValue) return;
  const root = start + ((-startValue) * (end - start)) / (endValue - startValue);
  if (root > start && root < end) roots.push(root);
};

export function willDanmakuCollide(
  existing: DanmakuMotion,
  candidate: DanmakuMotion,
  viewportWidth: number,
  gap = DANMAKU_GAP_PX,
): boolean {
  if (
    !Number.isFinite(existing.startedAt)
    || !Number.isFinite(existing.durationMs)
    || existing.durationMs <= 0
    || !Number.isFinite(existing.width)
    || existing.width <= 0
    || !Number.isFinite(candidate.startedAt)
    || !Number.isFinite(candidate.durationMs)
    || candidate.durationMs <= 0
    || !Number.isFinite(candidate.width)
    || candidate.width <= 0
    || !Number.isFinite(viewportWidth)
    || viewportWidth <= 0
  ) {
    return true;
  }

  const start = Math.max(existing.startedAt, candidate.startedAt);
  const end = Math.min(
    existing.startedAt + existing.durationMs,
    candidate.startedAt + candidate.durationMs,
  );
  if (end <= start) return false;
  const safeGap = Number.isFinite(gap) ? Math.max(0, gap) : DANMAKU_GAP_PX;

  const existingStart = getDanmakuBounds(existing, start, viewportWidth);
  const existingEnd = getDanmakuBounds(existing, end, viewportWidth);
  const candidateStart = getDanmakuBounds(candidate, start, viewportWidth);
  const candidateEnd = getDanmakuBounds(candidate, end, viewportWidth);
  const firstStart = candidateStart.left - existingStart.right - safeGap;
  const firstEnd = candidateEnd.left - existingEnd.right - safeGap;
  const secondStart = candidateStart.right + safeGap - existingStart.left;
  const secondEnd = candidateEnd.right + safeGap - existingEnd.left;
  const roots: number[] = [];
  addRootBetween(roots, start, end, firstStart, firstEnd);
  addRootBetween(roots, start, end, secondStart, secondEnd);
  addRootBetween(roots, start, end, existingStart.right, existingEnd.right);
  addRootBetween(roots, start, end, existingStart.left - viewportWidth, existingEnd.left - viewportWidth);
  addRootBetween(roots, start, end, candidateStart.right, candidateEnd.right);
  addRootBetween(roots, start, end, candidateStart.left - viewportWidth, candidateEnd.left - viewportWidth);
  const boundaries = [start, ...roots.sort((first, second) => first - second), end];

  for (let index = 0; index < boundaries.length - 1; index += 1) {
    const sample = (boundaries[index] + boundaries[index + 1]) / 2;
    if (collisionAt(existing, candidate, sample, viewportWidth, safeGap)) return true;
  }
  return false;
}

export function findSafeTrack(
  activeItems: readonly TrackDanmakuMotion[],
  candidate: DanmakuMotion,
  trackCount: number,
  viewportWidth: number,
  startTrack: number,
  now: number,
  entryIntervalMs: number,
  gap = DANMAKU_GAP_PX,
): number {
  const count = Math.max(0, Math.floor(trackCount));
  if (count === 0 || !Number.isFinite(now)) return -1;
  const normalizedStart = ((Math.floor(startTrack) % count) + count) % count;
  for (let offset = 0; offset < count; offset += 1) {
    const track = (normalizedStart + offset) % count;
    const sameTrackItems = activeItems.filter((item) => item.track === track);
    const entryBlocked = sameTrackItems.some(
      (item) => getDanmakuEntryReadyAt(item, viewportWidth, entryIntervalMs) > now,
    );
    const hasCollision = sameTrackItems.some(
      (item) => willDanmakuCollide(item, candidate, viewportWidth, gap),
    );
    if (!entryBlocked && !hasCollision) return track;
  }
  return -1;
}
