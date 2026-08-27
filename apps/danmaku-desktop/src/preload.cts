import { contextBridge, ipcRenderer } from "electron";

type OverlaySessionListener = (session: unknown) => void;
const overlaySessionListeners = new Set<OverlaySessionListener>();

ipcRenderer.on("danmaku:overlay-session", (_event, session: unknown) => {
  overlaySessionListeners.forEach((listener) => listener(session));
});

contextBridge.exposeInMainWorld("danmakuDesktop", {
  listDisplays: () => ipcRenderer.invoke("danmaku:list-displays"),
  start: (request: unknown) => ipcRenderer.invoke("danmaku:start", request),
  stop: () => ipcRenderer.invoke("danmaku:stop"),
  resume: () => ipcRenderer.invoke("danmaku:resume"),
  getOverlaySession: () => ipcRenderer.invoke("danmaku:get-overlay-session"),
  onOverlaySession: (listener: OverlaySessionListener) => {
    overlaySessionListeners.add(listener);
    return () => overlaySessionListeners.delete(listener);
  },
});
