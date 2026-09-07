import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));

const mainSource = await readFile(new URL("../src/main.ts", import.meta.url), "utf8");
const preloadSource = await readFile(new URL("../src/preload.cts", import.meta.url), "utf8");
const launcherSource = await readFile(new URL("../launcher/launcher.js", import.meta.url), "utf8");

assert.match(mainSource, /remembered-token\.js/);
assert.ok(packageJson.build.files.includes("dist/remembered-token.js"));
assert.match(mainSource, /saveRememberedToken\(rememberedTokenFile\(\), request\.token, safeStorage\)/);
assert.match(mainSource, /danmaku:get-remembered-token/);
assert.match(preloadSource, /getRememberedToken: \(\) => ipcRenderer\.invoke\("danmaku:get-remembered-token"\)/);
assert.match(launcherSource, /window\.danmakuDesktop\.getRememberedToken\(\)/);
assert.match(launcherSource, /token\.value = rememberedToken/);
assert.doesNotMatch(`${mainSource}${preloadSource}${launcherSource}`, /localStorage/);

const { loadRememberedToken, saveRememberedToken } = await import("../dist/remembered-token.js");
const files = new Map();
const fileSystem = {
  readFile: async (filePath) => {
    const value = files.get(filePath);
    if (!value) {
      const error = new Error("missing token file");
      error.code = "ENOENT";
      throw error;
    }
    return value;
  },
  writeFile: async (filePath, value) => {
    files.set(filePath, Buffer.from(value));
  },
};
const secureStorage = {
  isEncryptionAvailable: () => true,
  encryptString: (value) => Buffer.from([...value].reverse().join(""), "utf8"),
  decryptString: (value) => [...Buffer.from(value).toString("utf8")].reverse().join(""),
};
const tokenPath = "last-token.bin";
const token = "dm1.activity-id.1.signature";

assert.equal(await saveRememberedToken(tokenPath, `  ${token}  `, secureStorage, fileSystem), true);
assert.ok(files.has(tokenPath));
assert.notEqual(files.get(tokenPath).toString("utf8"), token);
assert.equal(await loadRememberedToken(tokenPath, secureStorage, fileSystem), token);
assert.equal(await saveRememberedToken(tokenPath, "   ", secureStorage, fileSystem), false);

const unavailableStorage = { ...secureStorage, isEncryptionAvailable: () => false };
assert.equal(await saveRememberedToken("unavailable.bin", token, unavailableStorage, fileSystem), false);
assert.equal(await loadRememberedToken(tokenPath, unavailableStorage, fileSystem), "");

console.log("danmaku token memory assertions passed");
