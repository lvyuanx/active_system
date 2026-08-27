/// <reference types="vite/client" />

import type { DanmakuOverlayBootstrap } from "./api/client";

interface DanmakuDesktopBridge {
  getOverlaySession: () => Promise<DanmakuOverlayBootstrap | null>;
  onOverlaySession: (listener: (session: DanmakuOverlayBootstrap) => void) => () => void;
}

declare global {
  interface Window {
    danmakuDesktop?: DanmakuDesktopBridge;
  }
}

export {};
