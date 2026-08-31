export interface GlobePoint {
  x: number;
  y: number;
  z: number;
}

export interface GlobeRotation {
  x: number;
  y: number;
}

export interface GlobeRotationMatrix {
  cosX: number;
  sinX: number;
  cosY: number;
  sinY: number;
}

export interface GlobeRenderProfile {
  avatarLimit: number;
  labelLimit: number;
  minAvatarZ: number;
  minLabelZ: number;
  avatarScale: number;
  maxAvatarSize: number;
  nameScale: number;
  frameStride: number;
  pixelRatioCap: number;
}

export interface ProjectedGlobePoint extends GlobePoint {
  x: number;
  y: number;
  scale: number;
  alpha: number;
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const TWO_PI = Math.PI * 2;

export function createGlobeRotationMatrix(rotation: GlobeRotation): GlobeRotationMatrix {
  return {
    cosX: Math.cos(rotation.x),
    sinX: Math.sin(rotation.x),
    cosY: Math.cos(rotation.y),
    sinY: Math.sin(rotation.y),
  };
}

export function rotateGlobePointInto(
  point: GlobePoint,
  matrix: GlobeRotationMatrix,
  target: GlobePoint,
): void {
  const yawX = point.x * matrix.cosY + point.z * matrix.sinY;
  const yawZ = -point.x * matrix.sinY + point.z * matrix.cosY;
  target.x = yawX;
  target.y = point.y * matrix.cosX - yawZ * matrix.sinX;
  target.z = point.y * matrix.sinX + yawZ * matrix.cosX;
}

export function globeRenderProfile(
  participantCount: number,
  width: number,
  height: number,
): GlobeRenderProfile {
  if (participantCount <= 80) {
    return {
      avatarLimit: participantCount,
      labelLimit: participantCount,
      minAvatarZ: -0.9,
      minLabelZ: -0.7,
      avatarScale: 1,
      maxAvatarSize: 48,
      nameScale: 1,
      frameStride: 1,
      pixelRatioCap: 2,
    };
  }
  if (participantCount <= 160) {
    return {
      avatarLimit: Math.min(participantCount, 120),
      labelLimit: 68,
      minAvatarZ: -0.35,
      minLabelZ: 0.02,
      avatarScale: 0.92,
      maxAvatarSize: 38,
      nameScale: 0.9,
      frameStride: 1,
      pixelRatioCap: 1.75,
    };
  }
  if (participantCount <= 260) {
    return {
      avatarLimit: 110,
      labelLimit: 56,
      minAvatarZ: -0.05,
      minLabelZ: 0.18,
      avatarScale: 0.86,
      maxAvatarSize: 31,
      nameScale: 0.82,
      frameStride: 2,
      pixelRatioCap: 1.5,
    };
  }
  const areaScale = Math.min(1, Math.max(0.78, Math.min(width || 720, height || 720) / 720));
  return {
    avatarLimit: 120,
    labelLimit: Math.round(48 * areaScale),
    minAvatarZ: 0.05,
    minLabelZ: 0.25,
    avatarScale: 0.84,
    maxAvatarSize: 26,
    nameScale: 0.76,
    frameStride: 2,
    pixelRatioCap: 1.25,
  };
}

export function fibonacciSphere(count: number): GlobePoint[] {
  if (!Number.isFinite(count) || count <= 0) return [];
  return Array.from({ length: Math.floor(count) }, (_, index) => {
    const y = 1 - ((index + 0.5) / count) * 2;
    const radius = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = GOLDEN_ANGLE * index;
    return { x: Math.cos(theta) * radius, y, z: Math.sin(theta) * radius };
  });
}

export function rotateGlobePoint(point: GlobePoint, rotation: GlobeRotation): GlobePoint {
  const target = { x: 0, y: 0, z: 0 };
  rotateGlobePointInto(point, createGlobeRotationMatrix(rotation), target);
  return target;
}

export function projectGlobePoint(
  point: GlobePoint,
  width: number,
  height: number,
  radius: number,
): ProjectedGlobePoint {
  const perspective = 3.2;
  const scale = perspective / (perspective - point.z);
  return {
    ...point,
    x: width / 2 + point.x * radius * scale,
    y: height / 2 + point.y * radius * scale,
    scale,
    alpha: 0.2 + ((point.z + 1) / 2) * 0.8,
  };
}

export function shortestAngleDelta(from: number, to: number): number {
  let delta = (to - from) % TWO_PI;
  if (delta > Math.PI) delta -= TWO_PI;
  if (delta < -Math.PI) delta += TWO_PI;
  return delta;
}

export function winnerTargetRotation(
  point: GlobePoint,
  current: GlobeRotation,
  extraTurns = 2,
): GlobeRotation {
  const targetYaw = Math.atan2(-point.x, point.z);
  const targetPitch = Math.atan2(point.y, Math.hypot(point.x, point.z));
  return {
    x: current.x + shortestAngleDelta(current.x, targetPitch),
    y: current.y + shortestAngleDelta(current.y, targetYaw) + TWO_PI * extraTurns,
  };
}

export function easeOutCubic(progress: number): number {
  const clamped = Math.min(1, Math.max(0, progress));
  return 1 - (1 - clamped) ** 3;
}

export function globeScatterScale(progress: number, depth: number): number {
  const normalizedDepth = Math.min(1, Math.max(-1, depth));
  return 1 + easeOutCubic(progress) * (0.85 + ((normalizedDepth + 1) / 2) * 0.3);
}
