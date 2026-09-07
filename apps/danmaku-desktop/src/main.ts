import {
  app,
  BrowserWindow,
  globalShortcut,
  ipcMain,
  Menu,
  nativeImage,
  safeStorage,
  screen,
  Tray,
} from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { loadRememberedToken, saveRememberedToken } from "./remembered-token.js";

type DanmakuSettings = {
  track_count: number;
  font_size: number;
  opacity: number;
  duration_seconds: number;
  entry_interval_seconds: number;
  max_wait_seconds: number;
  display_top: number;
  display_bottom: number;
  text_color: string;
};
type DanmakuSession = {
  activity_id: string;
  activity_name: string;
  activity_status: "closed" | "open" | "ended";
  settings: DanmakuSettings;
  latest_message_id: number;
};
type OverlayBootstrap = {
  apiBaseUrl: string;
  token: string;
  session: DanmakuSession;
};
type StartRequest = {
  apiBaseUrl: string;
  token: string;
  displayIds: number[];
};
type DisplayOption = {
  id: number;
  label: string;
  width: number;
  height: number;
  isPrimary: boolean;
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
let launcherWindow: BrowserWindow | undefined;
const overlayWindows = new Map<number, BrowserWindow>();
let tray: Tray | undefined;
let runtime: OverlayBootstrap & { displayIds: number[] } | undefined;
let isQuitting = false;

const isLauncherSender = (sender: Electron.WebContents) => sender === launcherWindow?.webContents;
const isOverlaySender = (sender: Electron.WebContents) =>
  [...overlayWindows.values()].some((window) => window.webContents === sender);
const launcherFile = () => path.join(app.getAppPath(), "launcher", "index.html");
const rememberedTokenFile = () => path.join(app.getPath("userData"), "danmaku-token.bin");
const preloadFile = () => path.join(__dirname, "preload.cjs");
const overlayURL = () => `${process.env.DANMAKU_SCREEN_DEV_URL ?? "http://localhost:5174"}/?danmaku-overlay=1`;
const packagedOverlayFile = () => path.join(process.resourcesPath, "screen-web", "index.html");

function normalizeApiBaseUrl(value: unknown): string {
  if (typeof value !== "string") throw new Error("API 地址无效");
  const url = new URL(value.trim());
  if (!/^https?:$/.test(url.protocol) || url.username || url.password) {
    throw new Error("API 地址必须使用 http 或 https 协议");
  }
  return url.toString().replace(/\/$/, "");
}

function parseStartRequest(value: unknown): StartRequest {
  if (!value || typeof value !== "object") throw new Error("启动参数无效");
  const candidate = value as Partial<StartRequest> & { displayId?: unknown };
  const token = typeof candidate.token === "string" ? candidate.token.trim() : "";
  if (!token || token.length > 4096) throw new Error("请粘贴有效的弹幕 token");
  const requestedDisplayIds = Array.isArray(candidate.displayIds)
    ? candidate.displayIds
    : Number.isInteger(candidate.displayId) ? [candidate.displayId] : [];
  if (requestedDisplayIds.length === 0 || requestedDisplayIds.some((id) => !Number.isInteger(id))) {
    throw new Error("请至少选择一个投屏显示器");
  }
  return {
    apiBaseUrl: normalizeApiBaseUrl(candidate.apiBaseUrl),
    token,
    displayIds: [...new Set(requestedDisplayIds as number[])],
  };
}

function listDisplays(): DisplayOption[] {
  const primaryDisplay = screen.getPrimaryDisplay();
  return screen.getAllDisplays().map((display, index) => ({
    id: display.id,
    label: display.label || `显示器 ${index + 1}`,
    width: display.bounds.width,
    height: display.bounds.height,
    isPrimary: display.id === primaryDisplay.id,
  }));
}

async function fetchSession(apiBaseUrl: string, token: string): Promise<DanmakuSession> {
  const response = await fetch(`${apiBaseUrl}/danmaku/session`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await response.json().catch(() => ({})) as Partial<DanmakuSession> & { detail?: string };
  if (!response.ok) throw new Error(body.detail ?? "无法加载弹幕配置");
  if (!body.activity_id || !body.settings || typeof body.latest_message_id !== "number") {
    throw new Error("弹幕服务返回了无效的会话信息");
  }
  return body as DanmakuSession;
}

function createLauncherWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 680,
    height: 720,
    minWidth: 600,
    minHeight: 640,
    show: false,
    backgroundColor: "#f3f5f4",
    webPreferences: {
      preload: preloadFile(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.setMenuBarVisibility(false);
  void window.loadFile(launcherFile());
  window.once("ready-to-show", () => window.show());
  window.on("close", (event) => {
    if (runtime && !isQuitting) {
      event.preventDefault();
      window.hide();
    }
  });
  window.on("closed", () => {
    if (launcherWindow === window) launcherWindow = undefined;
  });
  return window;
}

function sendOverlaySession(window: BrowserWindow): void {
  if (!runtime || window.isDestroyed()) return;
  window.webContents.send("danmaku:overlay-session", runtime);
}

function createOverlayWindow(displayId: number): void {
  if (!runtime) throw new Error("没有可恢复的弹幕会话");
  const display = screen.getAllDisplays().find((item) => item.id === displayId);
  if (!display) throw new Error("所选显示器已不可用");
  overlayWindows.get(displayId)?.destroy();
  const window = new BrowserWindow({
    x: display.bounds.x,
    y: display.bounds.y,
    width: display.bounds.width,
    height: display.bounds.height,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    focusable: false,
    skipTaskbar: true,
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    hasShadow: false,
    show: false,
    webPreferences: {
      preload: preloadFile(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  });
  overlayWindows.set(displayId, window);
  window.setIgnoreMouseEvents(true, { forward: true });
  window.setAlwaysOnTop(true, "screen-saver");
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  window.once("ready-to-show", () => {
    sendOverlaySession(window);
    window.showInactive();
  });
  window.webContents.on("did-finish-load", () => sendOverlaySession(window));
  window.on("closed", () => {
    if (overlayWindows.get(displayId) === window) overlayWindows.delete(displayId);
    refreshTrayMenu();
  });
  if (app.isPackaged) {
    void window.loadFile(packagedOverlayFile(), { query: { "danmaku-overlay": "1" } });
  } else {
    void window.loadURL(overlayURL());
  }
  refreshTrayMenu();
}

function createOverlayWindows(): void {
  if (!runtime) throw new Error("没有可恢复的弹幕会话");
  const availableDisplayIds = runtime.displayIds.filter((displayId) =>
    screen.getAllDisplays().some((display) => display.id === displayId),
  );
  if (availableDisplayIds.length === 0) throw new Error("所选显示器已不可用");
  stopOverlay();
  availableDisplayIds.forEach(createOverlayWindow);
}

function stopOverlay(): void {
  const windows = [...overlayWindows.values()];
  overlayWindows.clear();
  windows.forEach((window) => {
    if (!window.isDestroyed()) window.destroy();
  });
  refreshTrayMenu();
}

function openLauncher(): void {
  if (!launcherWindow) launcherWindow = createLauncherWindow();
  launcherWindow.show();
  launcherWindow.focus();
}

function toggleOverlay(): void {
  if (overlayWindows.size > 0) {
    stopOverlay();
    openLauncher();
    return;
  }
  if (!runtime) {
    openLauncher();
    return;
  }
  createOverlayWindows();
  launcherWindow?.hide();
}

function trayIcon(): Electron.NativeImage {
  const svg = [
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'>",
    "<rect width='32' height='32' rx='5' fill='#17211e'/>",
    "<path d='M8 22 16 7l8 15h-4l-4-8-4 8z' fill='#77d2b5'/></svg>",
  ].join("");
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`);
}

function refreshTrayMenu(): void {
  if (!tray) return;
  const isRunning = overlayWindows.size > 0;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: isRunning ? "停止弹幕" : "恢复弹幕", enabled: Boolean(runtime), click: toggleOverlay },
    { label: "打开控制台", click: openLauncher },
    { type: "separator" },
    { label: "退出", click: () => app.quit() },
  ]));
}

function createTray(): void {
  tray = new Tray(trayIcon());
  tray.setToolTip("ACTIVE 弹幕工具");
  tray.on("click", openLauncher);
  refreshTrayMenu();
}

function installIpcHandlers(): void {
  ipcMain.handle("danmaku:list-displays", (event) => {
    if (!isLauncherSender(event.sender)) throw new Error("未授权的显示器请求");
    return listDisplays();
  });
  ipcMain.handle("danmaku:start", async (event, value: unknown) => {
    if (!isLauncherSender(event.sender)) throw new Error("未授权的启动请求");
    const request = parseStartRequest(value);
    const session = await fetchSession(request.apiBaseUrl, request.token);
    const availableDisplayIds = new Set(screen.getAllDisplays().map((display) => display.id));
    if (request.displayIds.some((displayId) => !availableDisplayIds.has(displayId))) {
      throw new Error("所选显示器已不可用");
    }
    runtime = { ...request, session };
    createOverlayWindows();
    launcherWindow?.hide();
    await saveRememberedToken(rememberedTokenFile(), request.token, safeStorage);
    return session;
  });
  ipcMain.handle("danmaku:get-remembered-token", async (event) => {
    if (!isLauncherSender(event.sender)) throw new Error("未授权的 token 请求");
    return loadRememberedToken(rememberedTokenFile(), safeStorage);
  });
  ipcMain.handle("danmaku:stop", (event) => {
    if (!isLauncherSender(event.sender)) throw new Error("未授权的停止请求");
    stopOverlay();
  });
  ipcMain.handle("danmaku:resume", (event) => {
    if (!isLauncherSender(event.sender)) throw new Error("未授权的恢复请求");
    if (!runtime) throw new Error("没有可恢复的弹幕会话");
    createOverlayWindows();
    launcherWindow?.hide();
  });
  ipcMain.handle("danmaku:get-overlay-session", (event) => {
    if (!isOverlaySender(event.sender)) throw new Error("未授权的弹幕会话请求");
    return runtime;
  });
}

app.whenReady().then(() => {
  installIpcHandlers();
  launcherWindow = createLauncherWindow();
  createTray();
  globalShortcut.register("CommandOrControl+Shift+D", toggleOverlay);
  screen.on("display-removed", (_event, display) => {
    if (!runtime?.displayIds.includes(display.id)) return;
    runtime.displayIds = runtime.displayIds.filter((displayId) => displayId !== display.id);
    const window = overlayWindows.get(display.id);
    overlayWindows.delete(display.id);
    if (window && !window.isDestroyed()) window.destroy();
    if (runtime.displayIds.length === 0) {
      stopOverlay();
      runtime = undefined;
      openLauncher();
      return;
    }
    refreshTrayMenu();
  });
  app.on("activate", openLauncher);
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin" && !runtime) app.quit();
});
