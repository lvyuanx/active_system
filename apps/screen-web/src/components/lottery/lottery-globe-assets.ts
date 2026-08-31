export interface AvatarCache {
  onLoaded?: () => void;
  loadAvatar: (avatarId: number) => void;
  getAvatarBitmap: (avatarId: number, size: number) => HTMLCanvasElement | undefined;
}

export function createAvatarCache(sources: Record<number, string>): AvatarCache {
  const images = new Map<number, HTMLImageElement>();
  const bitmaps = new Map<string, HTMLCanvasElement>();
  const sizeBucket = (size: number) => Math.min(48, Math.max(12, Math.round(size / 4) * 4));
  const clearBitmaps = (avatarId: number) => {
    for (const key of bitmaps.keys()) {
      if (key.startsWith(`${avatarId}:`)) bitmaps.delete(key);
    }
  };
  const cache: AvatarCache = {
    loadAvatar: (avatarId) => {
      if (images.has(avatarId)) return;
      const image = new Image();
      image.decoding = "async";
      image.src = sources[avatarId] || sources[1];
      image.onload = () => {
        clearBitmaps(avatarId);
        cache.onLoaded?.();
      };
      images.set(avatarId, image);
    },
    getAvatarBitmap: (avatarId, size) => {
      const image = images.get(avatarId);
      if (!image?.complete || image.naturalWidth <= 0) return undefined;
      const bucket = sizeBucket(size);
      const key = `${avatarId}:${bucket}`;
      const cached = bitmaps.get(key);
      if (cached) return cached;
      const bitmap = document.createElement("canvas");
      bitmap.width = bucket;
      bitmap.height = bucket;
      const bitmapContext = bitmap.getContext("2d");
      if (!bitmapContext) return undefined;
      bitmapContext.imageSmoothingEnabled = true;
      bitmapContext.imageSmoothingQuality = "high";
      bitmapContext.beginPath();
      bitmapContext.arc(bucket / 2, bucket / 2, bucket / 2, 0, Math.PI * 2);
      bitmapContext.clip();
      bitmapContext.drawImage(image, 0, 0, bucket, bucket);
      bitmaps.set(key, bitmap);
      return bitmap;
    },
  };
  return cache;
}
