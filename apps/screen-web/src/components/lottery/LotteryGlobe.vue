<template>
  <div
    ref="host"
    class="lottery-globe"
    :data-phase="phase"
    :data-participant-count="participants.length"
  >
    <canvas
      ref="canvas"
      class="lottery-globe-canvas"
      role="img"
      :aria-label="`抽奖用户球体，共 ${participants.length} 位参与者`"
    />
    <div v-if="phase === 'revealed' && winnerName" class="globe-winner" data-winner-card aria-live="polite">
      <img :src="avatarSources[winnerAvatarId] || avatarSources[1]" alt="" />
      <span>{{ winnerName }}</span>
    </div>
    <p class="globe-caption">{{ phaseCaption }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { LotteryDraw, LotteryRoundParticipant } from "../../api/client";
import { avatarSources } from "./avatar-sources";
import { renderGlobeGuide as renderGlobeGuideToCanvas } from "./lottery-globe-canvas";
import { createAvatarCache } from "./lottery-globe-assets";
import {
  createGlobeRotationMatrix,
  easeOutCubic,
  fibonacciSphere,
  globeRenderProfile,
  globeScatterScale,
  rotateGlobePointInto,
  type GlobePoint,
  type GlobeRenderProfile,
  type GlobeRotation,
} from "./lottery-globe-math";

type GlobePhase = "idle" | "rolling" | "scattering" | "scattered" | "selecting" | "revealed";

const props = defineProps<{
  participants: LotteryRoundParticipant[];
  phase: GlobePhase;
  winnerId?: number | null;
  winner?: LotteryDraw["winner"] | null;
  roundId?: string;
  startedAt?: string;
}>();

const emit = defineEmits<{ scattered: []; settled: [] }>();
const host = ref<HTMLDivElement>();
const canvas = ref<HTMLCanvasElement>();
const winnerId = computed(() => props.winnerId ?? props.winner?.activity_user_id);
const winnerParticipant = computed(() => props.participants.find(
  (participant) => participant.activity_user_id === winnerId.value,
));
const winnerName = computed(() => winnerParticipant.value?.username || props.winner?.username);
const winnerAvatarId = computed(() => winnerParticipant.value?.avatar_id || 1);
const phaseCaption = computed(() => ({
  idle: "等待抽奖",
  rolling: "所有参与者正在滚动",
  scattering: "球体正在散开",
  scattered: "等待中奖者聚焦",
  selecting: "幸运者正在聚焦",
  revealed: "中奖者",
}[props.phase]));

interface GlobeEntry { participant: LotteryRoundParticipant; point: GlobePoint; rotated: GlobePoint }

interface ProjectedGlobeEntry {
  entry: GlobeEntry;
  x: number;
  y: number;
  z: number;
  scale: number;
  alpha: number;
  focusDistance: number;
  imageSize: number;
  nameSize: number;
  visible: boolean;
  showAvatar: boolean;
  showName: boolean;
}

interface LabelPlacement { left: number; right: number; top: number; bottom: number; maxWidth: number }

interface VisualGlobeEntry { x: number; y: number; size: number; alpha: number; nameSize: number }

const entries: GlobeEntry[] = [];
const projectedEntries: ProjectedGlobeEntry[] = [];
const labelPlacements: LabelPlacement[] = [];
const avatarCache = createAvatarCache(avatarSources);
let context: CanvasRenderingContext2D | null = null;
let guideCanvas: HTMLCanvasElement | undefined;
let frameHandle: number | undefined;
let resizeObserver: ResizeObserver | undefined;
let width = 0;
let height = 0;
let pixelRatio = 1;
let profile: GlobeRenderProfile = globeRenderProfile(0, 720, 720);
let frameCounter = 0;
let rotation: GlobeRotation = { x: -0.08, y: 0 };
let scatterStartedAt = 0;
let scatterProgress = 0;
let selectionStartedAt = 0;
let selectionProgress = 0;
let lastFrame = 0;
let scatteredEmitted = false;
let settledEmitted = false;

const prefersReducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

const seedFromRound = (roundId: string | undefined) => {
  if (!roundId) return 0;
  let hash = 2166136261;
  for (const character of roundId) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return (hash >>> 0) / 4294967296;
};

const rebuildEntries = () => {
  entries.splice(0, entries.length);
  projectedEntries.splice(0, projectedEntries.length);
  const points = fibonacciSphere(props.participants.length);
  props.participants.forEach((participant, index) => {
    const point = points[index] || { x: 0, y: 0, z: 1 };
    entries.push({ participant, point, rotated: { x: 0, y: 0, z: 0 } });
    avatarCache.loadAvatar(participant.avatar_id);
  });
};

const resetRotation = () => {
  const startTime = props.startedAt ? Date.parse(props.startedAt) : NaN;
  const elapsed = Number.isFinite(startTime) ? Math.max(0, Date.now() - startTime) / 1000 : 0;
  rotation = { x: -0.08, y: seedFromRound(props.roundId) * Math.PI * 2 + elapsed * 0.72 };
  scatterStartedAt = 0;
  scatterProgress = 0;
  selectionStartedAt = 0;
  selectionProgress = 0;
  lastFrame = 0;
  frameCounter = 0;
  scatteredEmitted = false;
  settledEmitted = false;
};

const renderGlobeGuide = (radius: number) => {
  if (!width || !height) return;
  guideCanvas ??= document.createElement("canvas");
  renderGlobeGuideToCanvas(guideCanvas, width, height, pixelRatio, radius);
};

const resize = () => {
  if (!host.value || !canvas.value || !context) return;
  width = host.value.clientWidth;
  height = host.value.clientHeight;
  profile = globeRenderProfile(props.participants.length, width, height);
  const deviceRatio = Math.min(2, window.devicePixelRatio || 1);
  const pixelBudget = 2_400_000;
  const areaRatio = width * height ? Math.sqrt(pixelBudget / (width * height)) : deviceRatio;
  pixelRatio = Math.min(deviceRatio, profile.pixelRatioCap, Math.max(0.75, areaRatio));
  canvas.value.width = Math.max(1, Math.floor(width * pixelRatio));
  canvas.value.height = Math.max(1, Math.floor(height * pixelRatio));
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  renderGlobeGuide(Math.max(100, Math.min(width * 0.42, height * 0.42)));
  draw(true);
};

const isVisible = (projected: ProjectedGlobeEntry, radius: number) => projected.focusDistance <= radius * 1.08;
const isWinner = (projected: ProjectedGlobeEntry) => (
  projected.entry.participant.activity_user_id === winnerId.value
);

const createLabelPlacementAt = (
  x: number,
  y: number,
  size: number,
  nameSize: number,
  username: string,
): LabelPlacement => {
  const maxWidth = Math.max(size * 1.8, Math.min(size * 3.5, username.length * nameSize * 0.86));
  const centerY = y + size * 0.62;
  const halfWidth = maxWidth / 2 + 4;
  const halfHeight = nameSize * 0.72 + 3;
  return { left: x - halfWidth, right: x + halfWidth, top: centerY - 2, bottom: centerY + halfHeight, maxWidth };
};

const createLabelPlacement = (projected: ProjectedGlobeEntry) => createLabelPlacementAt(
  projected.x,
  projected.y,
  projected.imageSize,
  projected.nameSize,
  projected.entry.participant.username,
);

const canPlaceLabel = (placement: LabelPlacement) => !labelPlacements.some((current) => (
  placement.left < current.right
  && placement.right > current.left
  && placement.top < current.bottom
  && placement.bottom > current.top
));

const prepareProjectedEntries = (radius: number) => {
  const matrix = createGlobeRotationMatrix(rotation);
  const centerX = width / 2;
  const centerY = height / 2;
  const perspective = 3.2;
  projectedEntries.length = entries.length;
  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    const projected = projectedEntries[index] || {
      entry,
      x: 0,
      y: 0,
      z: 0,
      scale: 1,
      alpha: 0,
      focusDistance: 0,
      imageSize: 0,
      nameSize: 0,
      visible: false,
      showAvatar: false,
      showName: false,
    };
    projected.entry = entry;
    rotateGlobePointInto(entry.point, matrix, entry.rotated);
    projected.z = entry.rotated.z;
    projected.scale = perspective / (perspective - projected.z);
    projected.x = centerX + entry.rotated.x * radius * projected.scale;
    projected.y = centerY + entry.rotated.y * radius * projected.scale;
    projected.alpha = 0.2 + ((projected.z + 1) / 2) * 0.8;
    projected.focusDistance = Math.hypot(projected.x - centerX, projected.y - centerY);
    projected.visible = projected.focusDistance <= radius * 1.08;
    projected.imageSize = Math.min(
      profile.maxAvatarSize,
      Math.max(10, radius * 0.105 * projected.scale * profile.avatarScale),
    );
    projected.nameSize = Math.max(7, Math.min(15, projected.imageSize * 0.36 * profile.nameScale));
    projected.showAvatar = false;
    projected.showName = false;
    projectedEntries[index] = projected;
  }
  projectedEntries.sort((left, right) => left.z - right.z);
};

const selectDetailEntries = (radius: number) => {
  labelPlacements.length = 0;
  let labelCount = 0;
  let avatarCount = 0;
  for (let index = projectedEntries.length - 1; index >= 0; index -= 1) {
    const projected = projectedEntries[index];
    if (!isVisible(projected, radius)) continue;
    const winner = isWinner(projected);
    if (winner || (avatarCount < profile.avatarLimit && projected.z >= profile.minAvatarZ)) {
      projected.showAvatar = true;
      if (!winner) avatarCount += 1;
    }
    if (!winner && (labelCount >= profile.labelLimit || projected.z < profile.minLabelZ)) continue;
    const placement = createLabelPlacement(projected);
    if (winner || canPlaceLabel(placement)) {
      projected.showName = true;
      labelPlacements.push(placement);
      if (!winner) labelCount += 1;
    }
  }
};

const visualEntry = (projected: ProjectedGlobeEntry, radius: number): VisualGlobeEntry => {
  const centerX = width / 2;
  const centerY = height / 2;
  const scatter = props.phase === "scattering"
    ? easeOutCubic(scatterProgress)
    : props.phase === "scattered" || props.phase === "selecting" || props.phase === "revealed" ? 1 : 0;
  const spread = globeScatterScale(scatter, projected.z);
  let x = centerX + (projected.x - centerX) * spread;
  let y = centerY + (projected.y - centerY) * spread;
  let size = projected.imageSize * (1 - scatter * 0.28);
  let alpha = projected.alpha * (1 - scatter * 0.68);
  let nameSize = projected.nameSize;
  const focusPhase = props.phase === "selecting" || props.phase === "revealed";
  if (focusPhase) {
    const focusProgress = props.phase === "revealed" ? 1 : easeOutCubic(selectionProgress);
    if (isWinner(projected)) {
      const focusSize = Math.min(112, Math.max(76, radius * 0.28));
      x += (centerX - x) * focusProgress;
      y += (centerY - y) * focusProgress;
      size += (focusSize - size) * focusProgress;
      alpha += (1 - alpha) * focusProgress;
      nameSize = Math.max(projected.nameSize, Math.min(24, size * 0.32));
    } else {
      alpha *= 1 - focusProgress;
      size *= 1 - focusProgress * 0.42;
    }
  }
  return { x, y, size, alpha, nameSize };
};

const drawEntry = (projected: ProjectedGlobeEntry, radius: number) => {
  if (!context) return;
  const winner = isWinner(projected);
  if (props.phase === "revealed" && winner) return;
  const focusPhase = props.phase === "selecting" || props.phase === "revealed";
  const winnerSpotlight = winner && props.phase === "selecting";
  if (!projected.visible && !winnerSpotlight) return;
  const visual = visualEntry(projected, radius);
  if (visual.alpha < 0.02 && !winnerSpotlight) return;
  const showAvatar = projected.showAvatar || winnerSpotlight;
  const showName = projected.showName || winnerSpotlight;
  if (showAvatar) {
    context.globalAlpha = Math.min(1, visual.alpha + (winner ? 0.18 : 0));
    if (winnerSpotlight) {
      const pulse = Math.sin((props.phase === "selecting" ? selectionProgress : 1) * Math.PI);
      context.save();
      const halo = context.createRadialGradient(
        visual.x,
        visual.y,
        visual.size * 0.35,
        visual.x,
        visual.y,
        visual.size * 1.7,
      );
      halo.addColorStop(0, "rgba(101, 229, 211, 0.34)");
      halo.addColorStop(1, "rgba(101, 229, 211, 0)");
      context.globalAlpha = Math.min(1, 0.8 * visual.alpha);
      context.fillStyle = halo;
      context.beginPath();
      context.arc(visual.x, visual.y, visual.size * 1.7, 0, Math.PI * 2);
      context.fill();
      context.strokeStyle = "rgba(101, 229, 211, 0.95)";
      context.lineWidth = 3;
      context.shadowColor = "rgba(101, 229, 211, 0.9)";
      context.shadowBlur = 22;
      context.beginPath();
      context.arc(visual.x, visual.y, visual.size * (0.72 + pulse * 0.12), 0, Math.PI * 2);
      context.stroke();
      context.restore();
    }
    const bitmap = avatarCache.getAvatarBitmap(projected.entry.participant.avatar_id, visual.size);
    if (bitmap) {
      context.drawImage(bitmap, visual.x - visual.size / 2, visual.y - visual.size / 2, visual.size, visual.size);
    } else {
      context.fillStyle = winner ? "rgba(101, 229, 211, 0.78)" : "rgba(114, 102, 241, 0.7)";
      context.beginPath();
      context.arc(visual.x, visual.y, visual.size / 2, 0, Math.PI * 2);
      context.fill();
    }
  } else {
    context.globalAlpha = Math.max(0.08, visual.alpha * 0.52);
    context.fillStyle = "rgba(126, 132, 194, 0.85)";
    context.beginPath();
    context.arc(visual.x, visual.y, Math.max(1.5, visual.size * 0.16), 0, Math.PI * 2);
    context.fill();
  }
  if (showName) {
    const placement = winnerSpotlight
      ? createLabelPlacementAt(
        visual.x,
        visual.y,
        visual.size,
        visual.nameSize,
        projected.entry.participant.username,
      )
      : createLabelPlacement(projected);
    context.save();
    context.globalAlpha = Math.min(1, visual.alpha + (winner ? 0.2 : 0));
    context.fillStyle = winner ? "#eafffb" : "#c6c8e7";
    context.font = `${winner ? 700 : 550} ${visual.nameSize}px Inter, "PingFang SC", "Microsoft YaHei", sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "top";
    context.shadowColor = winner ? "rgba(101, 229, 211, 0.75)" : "transparent";
    context.shadowBlur = winner ? 10 : 0;
    context.fillText(
      projected.entry.participant.username,
      visual.x,
      visual.y + visual.size * 0.62,
      placement.maxWidth,
    );
    context.restore();
  }
  context.globalAlpha = 1;
};

const draw = (force = false) => {
  if (!context || !width || !height) return;
  const smoothPhase = props.phase === "scattering" || props.phase === "selecting";
  if (!force && !smoothPhase && profile.frameStride > 1 && frameCounter % profile.frameStride !== 0) return;
  const radius = Math.max(100, Math.min(width * 0.42, height * 0.42));
  context.globalAlpha = 1;
  context.clearRect(0, 0, width, height);
  if (!guideCanvas) renderGlobeGuide(radius);
  if (guideCanvas) context.drawImage(guideCanvas, 0, 0, width, height);
  prepareProjectedEntries(radius);
  selectDetailEntries(radius);
  const focusPhase = props.phase === "selecting" || props.phase === "revealed";
  if (!focusPhase) {
    for (const projected of projectedEntries) drawEntry(projected, radius);
    return;
  }
  for (const projected of projectedEntries) {
    if (!isWinner(projected)) drawEntry(projected, radius);
  }
  const winner = projectedEntries.find(isWinner);
  if (winner) drawEntry(winner, radius);
};

avatarCache.onLoaded = () => draw(true);

const announceScattered = () => {
  if (scatteredEmitted) return;
  scatteredEmitted = true;
  emit("scattered");
};

const settle = () => {
  if (settledEmitted) return;
  settledEmitted = true;
  emit("settled");
};

const animate = (time: number) => {
  frameHandle = undefined;
  frameCounter += 1;
  const delta = lastFrame ? Math.min(50, Math.max(8, time - lastFrame)) : 16;
  lastFrame = time;
  if (props.phase === "rolling") rotation.y += 0.72 * delta / 1000;
  if (props.phase === "scattering") {
    if (!scatterStartedAt) scatterStartedAt = time;
    const duration = prefersReducedMotion() ? 320 : 850;
    scatterProgress = Math.min(1, (time - scatterStartedAt) / duration);
    if (scatterProgress >= 1) announceScattered();
  }
  if (props.phase === "selecting") {
    if (!selectionStartedAt) selectionStartedAt = time;
    const duration = prefersReducedMotion() ? 520 : 1300;
    selectionProgress = Math.min(1, (time - selectionStartedAt) / duration);
    if (selectionProgress >= 1) settle();
  }
  draw();
  const shouldContinue = props.phase === "rolling"
    || (props.phase === "scattering" && !scatteredEmitted)
    || (props.phase === "selecting" && !settledEmitted);
  if (shouldContinue) frameHandle = window.requestAnimationFrame(animate);
};

const startAnimation = () => {
  if (frameHandle === undefined) frameHandle = window.requestAnimationFrame(animate);
};

watch(
  () => props.roundId,
  () => {
    rebuildEntries();
    resetRotation();
    draw(true);
    if (["rolling", "scattering", "selecting"].includes(props.phase)) startAnimation();
  },
  { immediate: true },
);

watch(
  () => props.phase,
  (phase) => {
    if (phase === "rolling") startAnimation();
    else if (phase === "scattering") {
      scatterStartedAt = 0;
      scatterProgress = 0;
      startAnimation();
    } else if (phase === "scattered") {
      scatterProgress = 1;
      draw(true);
    } else if (phase === "selecting") {
      scatterProgress = 1;
      selectionStartedAt = 0;
      selectionProgress = 0;
      startAnimation();
    } else {
      scatterProgress = phase === "revealed" ? 1 : scatterProgress;
      selectionProgress = phase === "revealed" ? 1 : selectionProgress;
      draw(true);
    }
  },
);

onMounted(() => {
  context = canvas.value?.getContext("2d") || null;
  resizeObserver = new ResizeObserver(resize);
  if (host.value) resizeObserver.observe(host.value);
  resize();
  if (["rolling", "scattering", "selecting"].includes(props.phase)) startAnimation();
});

onBeforeUnmount(() => {
  if (frameHandle !== undefined) window.cancelAnimationFrame(frameHandle);
  resizeObserver?.disconnect();
  context = null;
});
</script>

<style scoped src="./LotteryGlobe.css"></style>
