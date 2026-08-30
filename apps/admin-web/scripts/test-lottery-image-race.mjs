import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const sourcePath = fileURLToPath(new URL("../src/views/lottery/index.vue", import.meta.url));
const helperPath = fileURLToPath(new URL("../src/views/lottery/lottery-image-actions.ts", import.meta.url));
const source = readFileSync(sourcePath, "utf8");
const helper = readFileSync(helperPath, "utf8");
const guards = [
  "configRefreshVersion += 1;",
  "if (saving.value) return;",
  "refreshVersion === configRefreshVersion",
  "refreshLotteryAfterImages(activityId, applyConfig)",
  "target.pendingImage = action.file",
  "target.imageRemoved = true",
];

for (const guard of guards) {
  if (!source.includes(guard) && !helper.includes(guard)) {
    throw new Error(`缺少图片保存竞态保护：${guard}`);
  }
}
console.log("lottery image save race guards passed");
