export type RuntimeMode = "development" | "production";

// 开发者工具使用 development，体验版和正式版自动使用 production。

const runtimeConfigs: Record<RuntimeMode, { apiBaseUrl: string; wsBaseUrl: string }> = {
  development: {
    apiBaseUrl: "http://localhost:8000/api/v1",
    wsBaseUrl: "ws://localhost:8000/api/v1",
  },
  production: {
    apiBaseUrl: "https://active.lvyx.cc/api/v1",
    wsBaseUrl: "wss://active.lvyx.cc/api/v1",
  },
};

const detectRuntimeMode = (): RuntimeMode => {
  if (typeof wx === "undefined" || !wx.getAccountInfoSync) return "development";
  try {
    const envVersion = wx.getAccountInfoSync().miniProgram.envVersion;
    return envVersion === "develop" ? "development" : "production";
  } catch {
    return "development";
  }
};

export const runtimeMode: RuntimeMode = detectRuntimeMode();
let activeRuntimeConfig = runtimeConfigs[runtimeMode];

export const getRuntimeConfig = () => activeRuntimeConfig;

export const setRuntimeConfigFromOrigin = (origin: string) => {
  const normalized = origin.replace(/\/$/, "");
  if (!/^https?:\/\/[^/]+$/i.test(normalized)) return false;
  const host = normalized.replace(/^https?:\/\//i, "").split(":")[0].toLowerCase();
  if (host === "localhost" || host === "127.0.0.1" || host === "[::1]") return false;
  const wsOrigin = normalized.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
  activeRuntimeConfig = {
    apiBaseUrl: `${normalized}/api/v1`,
    wsBaseUrl: `${wsOrigin}/api/v1`,
  };
  return true;
};

export const runtimeConfig = runtimeConfigs[runtimeMode];
