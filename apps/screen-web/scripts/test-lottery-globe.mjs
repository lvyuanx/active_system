import assert from "node:assert/strict";
import {
  easeOutCubic,
  fibonacciSphere,
  globeRenderProfile,
  globeScatterScale,
  rotateGlobePoint,
  winnerTargetRotation,
} from "../dist-test/lottery/lottery-globe-math.js";

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
