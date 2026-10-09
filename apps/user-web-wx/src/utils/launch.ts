export interface LaunchOptionsLike {
  query?: Record<string, string | undefined>;
}

export interface ScanTarget {
  activityId?: string;
  origin?: string;
}

const normalizeActivityId = (value: unknown) => {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim();
  return normalized ? normalized : undefined;
};

const decodeScene = (value: string) => {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
};

export const parseActivityIdFromScanValue = (value: string): string | undefined => {
  const normalized = value.trim();
  if (!normalized) return undefined;

  const queryMatch = normalized.match(/[?&#](?:activity_id)=([^&#]+)/i);
  if (queryMatch) return normalizeActivityId(decodeScene(queryMatch[1]));

  const sceneMatch = normalized.match(/[?&#](?:scene)=([^&#]+)/i);
  if (sceneMatch) {
    const scene = decodeScene(sceneMatch[1]);
    const parsedScene = scene.match(/(?:^|&)activity_id=([^&]+)/);
    if (parsedScene) return normalizeActivityId(decodeScene(parsedScene[1]));
  }

  const pathMatch = normalized.match(/\/activity\/([^/?#]+)/i);
  return pathMatch ? normalizeActivityId(decodeScene(pathMatch[1])) : undefined;
};

export const parseScanTarget = (value: string): ScanTarget => {
  const normalized = value.trim();
  const originMatch = normalized.match(/^(https?):\/\/([^/]+)/i);
  const origin = originMatch ? `${originMatch[1].toLowerCase()}://${originMatch[2]}` : undefined;
  return {
    activityId: parseActivityIdFromScanValue(normalized),
    origin,
  };
};

export const parseActivityId = (options?: LaunchOptionsLike): string | undefined => {
  const query = options?.query ?? {};
  const direct = normalizeActivityId(query.activity_id);
  if (direct) return direct;

  const scene = normalizeActivityId(query.scene);
  if (!scene) return undefined;
  const decoded = decodeScene(scene);
  const match = decoded.match(/(?:^|&)activity_id=([^&]+)/);
  return normalizeActivityId(match?.[1] ?? decoded);
};
