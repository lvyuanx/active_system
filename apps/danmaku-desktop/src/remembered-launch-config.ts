import { readFile, writeFile } from "node:fs/promises";

const MAX_API_BASE_URL_LENGTH = 2048;
const MAX_DISPLAY_COUNT = 32;

export type RememberedLaunchConfig = {
  apiBaseUrl: string;
  displayIds: number[];
};

export type LaunchConfigFileSystem = {
  readFile: (filePath: string) => Promise<string>;
  writeFile: (filePath: string, data: string, options: { mode: number }) => Promise<void>;
};

const defaultFileSystem: LaunchConfigFileSystem = {
  readFile: (filePath) => readFile(filePath, "utf8"),
  writeFile: (filePath, data, options) => writeFile(filePath, data, options),
};

function normalizeApiBaseUrl(value: unknown): string {
  if (typeof value !== "string") return "";
  const rawValue = value.trim();
  if (!rawValue || rawValue.length > MAX_API_BASE_URL_LENGTH) return "";
  try {
    const url = new URL(rawValue);
    if (!/^https?:$/.test(url.protocol) || url.username || url.password) return "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return "";
  }
}

function normalizeDisplayIds(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((id): id is number => Number.isInteger(id)))]
    .slice(0, MAX_DISPLAY_COUNT);
}

function normalizeConfig(value: unknown): RememberedLaunchConfig | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<RememberedLaunchConfig>;
  const apiBaseUrl = normalizeApiBaseUrl(candidate.apiBaseUrl);
  const displayIds = normalizeDisplayIds(candidate.displayIds);
  if (!apiBaseUrl || displayIds.length === 0) return null;
  return { apiBaseUrl, displayIds };
}

export async function loadRememberedLaunchConfig(
  filePath: string,
  fileSystem: LaunchConfigFileSystem = defaultFileSystem,
): Promise<RememberedLaunchConfig | null> {
  try {
    return normalizeConfig(JSON.parse(await fileSystem.readFile(filePath)));
  } catch {
    return null;
  }
}

export async function saveRememberedLaunchConfig(
  filePath: string,
  config: RememberedLaunchConfig,
  fileSystem: LaunchConfigFileSystem = defaultFileSystem,
): Promise<boolean> {
  const normalizedConfig = normalizeConfig(config);
  if (!normalizedConfig) return false;
  try {
    await fileSystem.writeFile(filePath, `${JSON.stringify(normalizedConfig)}\n`, { mode: 0o600 });
    return true;
  } catch {
    return false;
  }
}
