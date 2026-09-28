import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  easeOutCubic,
  fibonacciSphere,
  globeRenderProfile,
  globeScatterScale,
  rotateGlobePoint,
  winnerTargetRotation,
  winnerFocusHandoff,
} from "../dist-test/lottery/lottery-globe-math.js";
import { latestLotteryDrawForPrize } from "../dist-test/lottery/lottery-selection.js";

const selectionDraws = [
  { draw_id: 1, prize_id: 10 },
  { draw_id: 3, prize_id: 20 },
  { draw_id: 5, prize_id: 10 },
];
assert.equal(latestLotteryDrawForPrize(selectionDraws, 10)?.draw_id, 5);
assert.equal(latestLotteryDrawForPrize(selectionDraws, 30), undefined);

const points = fibonacciSphere(120);
assert.equal(points.length, 120);
for (const point of points) {
  assert.ok(Math.abs(Math.hypot(point.x, point.y, point.z) - 1) < 1e-9);
}
const uniquePoints = new Set(points.map((point) => [point.x, point.y, point.z].join(",")));
assert.equal(uniquePoints.size, points.length);

const current = { x: -0.08, y: 2.7 };
const winner = points[73];
const target = winnerTargetRotation(winner, current, 2);
const settled = rotateGlobePoint(winner, target);
assert.ok(Math.abs(settled.x) < 1e-9);
assert.ok(Math.abs(settled.y) < 1e-9);
assert.ok(settled.z > 0.999999);
assert.equal(easeOutCubic(0), 0);
assert.equal(easeOutCubic(1), 1);
assert.ok(easeOutCubic(0.7) > 0.7);
assert.equal(globeScatterScale(0, 0), 1);
assert.ok(globeScatterScale(1, 1) > globeScatterScale(1, -1));
assert.ok(globeScatterScale(1, 0) > 1.8);
assert.equal(winnerFocusHandoff(0), 0);
assert.equal(winnerFocusHandoff(0.2), 0);
assert.equal(winnerFocusHandoff(0.6), 1);
assert.ok(winnerFocusHandoff(0.4) > 0);

const globeSource = readFileSync(new URL("../src/components/lottery/LotteryGlobe.vue", import.meta.url), "utf8");
const globeStyles = readFileSync(
  new URL("../src/components/lottery/LotteryGlobe.css", import.meta.url),
  "utf8",
);
const winnerSource = readFileSync(
  new URL("../src/components/lottery/LotteryWinnerReveal.vue", import.meta.url),
  "utf8",
);
const winnerStyles = readFileSync(
  new URL("../src/components/lottery/LotteryWinnerReveal.css", import.meta.url),
  "utf8",
);
const screenSource = readFileSync(
  new URL("../src/components/lottery/LotteryScreen.vue", import.meta.url),
  "utf8",
);
const screenImageStyles = readFileSync(
  new URL("../src/components/lottery/LotteryScreenImages.css", import.meta.url),
  "utf8",
);
const screenStyles = readFileSync(
  new URL("../src/components/lottery/LotteryScreen.css", import.meta.url),
  "utf8",
);
const screenIndex = readFileSync(new URL("../index.html", import.meta.url), "utf8");
assert.match(globeSource, /LotteryWinnerReveal/);
assert.match(winnerSource, /data-winner-focus/);
assert.match(winnerSource, /\(phase === 'selecting' \|\| phase === 'revealed'\) && winnerName/);
assert.doesNotMatch(winnerSource, /data-winner-card|class="globe-winner"/);
assert.match(globeSource, /winnerFocusHandoff\(selectionProgress\)/);
assert.match(winnerStyles, /@keyframes globe-winner-focus-in/);
assert.match(winnerStyles, /@media \(prefers-reduced-motion: reduce\)/);
assert.doesNotMatch(winnerStyles, /\.globe-winner\s*\{|@keyframes globe-winner-in/);
assert.match(screenSource, /activePrizeImageURL/);
assert.match(screenSource, /class="round-prize-chip__image"/);
assert.match(screenSource, /imageURL\(activePrizeImageURL\)/);
assert.match(screenSource, /markImageFailed\(activePrizeImageURL\)/);
assert.match(screenSource, /class="title-prize__image"/);
assert.match(screenSource, /displayPrizeImageURL/);
assert.match(screenSource, /class="winner-result__avatar"/);
assert.match(screenSource, /rememberWinnerAvatar/);
assert.match(screenSource, /class="prize-item"/);
assert.match(screenSource, /prizeDraws\(award, prize\.prize_id\)/);
assert.match(screenSource, /draw\.prize_id === prizeId/);
assert.doesNotMatch(screenSource, /winner-prize-image/);
assert.doesNotMatch(screenSource, /class="header-activity-name"|class="subtitle"/);
assert.doesNotMatch(screenSource, /CURRENT PRIZE|class="kicker"/);
assert.match(screenSource, /document\.title = activityName\?\.trim\(\) \|\| "幸运抽奖"/);
assert.match(screenImageStyles, /\.round-prize-chip__image\s*\{/);
assert.match(screenImageStyles, /\.title-prize__image\s*\{/);
assert.match(screenImageStyles, /width: 80px;\s*height: 80px/);
assert.match(screenImageStyles, /\.title-prize__image \{ width: 64px; height: 64px; \}/);
assert.match(screenStyles, /padding: clamp\(16px, 3vh, 38px\) 0/);
assert.match(screenStyles, /font-size: clamp\(24px, 3vw, 42px\)/);
assert.match(screenStyles, /margin-top: clamp\(14px, 2vh, 28px\)/);
assert.doesNotMatch(screenStyles, /\.header-activity-name\s*\{|\.subtitle\s*\{/);
assert.doesNotMatch(screenStyles, /\.kicker\s*\{/);
assert.match(screenIndex, /<title>幸运抽奖<\/title>/);
assert.match(screenSource, /'lottery-screen--immersive': activeRound/);
assert.match(screenSource, /restoreTimer = window\.setTimeout/);
assert.match(screenSource, /activeRound\.value = undefined/);
assert.match(screenStyles, /\.lottery-screen--immersive \.lottery-header/);
assert.match(screenStyles, /\.lottery-screen--immersive \.draw-layout/);
assert.match(screenStyles, /\.lottery-screen--immersive \.reveal-panel/);
assert.match(screenStyles, /\.winner-result__avatar\s*\{/);
assert.match(screenStyles, /\.prize-item \.winner-list/);
assert.match(globeStyles, /\.lottery-globe\[data-phase="rolling"\] \.globe-caption/);

const compactProfile = globeRenderProfile(300, 1280, 720);
assert.ok(compactProfile.avatarLimit < 300);
assert.ok(compactProfile.labelLimit <= 48);
assert.equal(compactProfile.frameStride, 2);
assert.ok(compactProfile.pixelRatioCap < 2);

const normalProfile = globeRenderProfile(60, 1280, 720);
assert.equal(normalProfile.avatarLimit, 60);
assert.equal(normalProfile.labelLimit, 60);
assert.equal(normalProfile.frameStride, 1);

const emptyProfile = globeRenderProfile(0, 1280, 720);
assert.equal(emptyProfile.avatarLimit, 0);
assert.equal(emptyProfile.labelLimit, 0);
console.log("lottery globe tests passed");
