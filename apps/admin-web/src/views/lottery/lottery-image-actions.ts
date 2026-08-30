import { deleteLotteryPrizeImage, getLottery, uploadLotteryPrizeImage } from "../../api/client";
import type { FormPrize } from "./lottery-config-form";

export interface PrizeImageAction {
  prizeId: number | null;
  name: string;
  file?: File;
  remove: boolean;
}

export const collectPrizeImageActions = (prizes: FormPrize[]): PrizeImageAction[] => prizes
  .filter((prize) => prize.pendingImage || prize.imageRemoved)
  .map((prize) => ({
    prizeId: prize.prize_id,
    name: prize.name,
    file: prize.pendingImage,
    remove: Boolean(prize.imageRemoved && !prize.pendingImage),
  }));

export const syncPrizeImages = async (
  activityId: string,
  prizes: FormPrize[],
  actions: PrizeImageAction[],
): Promise<boolean> => {
  let failed = false;
  for (const action of actions) {
    const target = prizes.find((prize) => (
      action.prizeId ? prize.prize_id === action.prizeId : prize.name === action.name
    ));
    if (!target?.prize_id) continue;
    target.imageLoading = true;
    target.imageError = undefined;
    try {
      const response = action.remove
        ? await deleteLotteryPrizeImage(activityId, target.prize_id)
        : await uploadLotteryPrizeImage(activityId, target.prize_id, action.file as File);
      target.image_url = response.image_url;
      target.pendingImage = undefined;
      target.previewUrl = undefined;
      target.imageRemoved = false;
    } catch (err) {
      failed = true;
      if (action.file) {
        if (target.previewUrl) URL.revokeObjectURL(target.previewUrl);
        target.pendingImage = action.file;
        target.previewUrl = URL.createObjectURL(action.file);
        target.imageRemoved = false;
      } else if (action.remove) {
        target.imageRemoved = true;
      }
      target.imageError = err instanceof Error ? err.message : "图片保存失败，请重试";
    } finally {
      target.imageLoading = false;
    }
  }
  return failed;
};

export const refreshLotteryAfterImages = async (
  activityId: string,
  applyConfig: (config: Awaited<ReturnType<typeof getLottery>>) => void,
) => {
  try {
    applyConfig(await getLottery(activityId));
  } catch {
    // 图片操作已完成时保留本地成功状态，后续手动刷新可重新读取配置。
  }
};
