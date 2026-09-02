import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [client, router, sidebar, page] = await Promise.all([
  read("../src/api/client.ts"),
  read("../src/router/index.ts"),
  read("../src/components/ActivitySidebar.vue"),
  read("../src/views/stickers/index.vue"),
]);

assert.match(client, /uploadChatSticker/);
assert.match(client, /disableChatSticker/);
assert.match(client, /restoreChatSticker/);
assert.match(router, /views\/stickers\/index\.vue/);
assert.match(sidebar, /active === ['"]stickers['"]/);
assert.match(sidebar, /goStickers/);
assert.match(page, /multiple/);
assert.match(page, /image\/gif/);
assert.match(page, /for \(const item of items\) await uploadOne\(item\)/);
assert.match(page, /历史消息仍会保留/);

console.log("admin chat sticker tests passed");
