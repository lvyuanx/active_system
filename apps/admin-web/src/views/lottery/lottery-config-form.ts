import {
  updateLottery,
  type LotteryConfig,
  type LotteryConfigUpdate,
} from "../../api/client";

export type FormAward = Omit<LotteryConfig["awards"][number], "award_id"> & {
  award_id: number | null;
};
export type FormPrize = Omit<LotteryConfig["prizes"][number], "prize_id" | "award_id"> & {
  prize_id: number | null;
  award_id: number;
  pendingImage?: File;
  previewUrl?: string;
  imageRemoved?: boolean;
  imageError?: string;
  imageLoading?: boolean;
};
export type LotteryForm = Omit<LotteryConfig, "awards" | "prizes"> & {
  awards: FormAward[];
  prizes: FormPrize[];
};

const savedId = (id: number | null): id is number => typeof id === "number" && id > 0;
const nameKey = (name: string) => name.trim().toLowerCase();

const basePayload = (
  form: LotteryForm,
): Pick<LotteryConfigUpdate, "no_repeat_across_prizes" | "rolling_name_count"> => ({
  no_repeat_across_prizes: form.no_repeat_across_prizes,
  rolling_name_count: form.rolling_name_count,
});

const awardPayload = (form: LotteryForm, allowTemporaryIds: boolean) => form.awards.map(
  ({ award_id, name, sort_order }) => ({
    award_id: allowTemporaryIds && !savedId(award_id) ? null : award_id,
    name,
    sort_order,
  }),
);

const prizePayload = (form: LotteryForm) => form.prizes.map(
  ({ prize_id, award_id, name, quantity, sort_order, is_enabled }) => ({
    prize_id,
    award_id,
    name,
    quantity,
    sort_order,
    is_enabled,
  }),
);

const validateForm = (form: LotteryForm) => {
  if (!form.awards.every((award) => award.name.trim()) || !form.prizes.every((prize) => prize.name.trim())) {
    throw new Error("奖项和奖品名称不能为空");
  }
  const awardIds = new Set(form.awards.map((award) => award.award_id));
  if (form.prizes.some((prize) => !awardIds.has(prize.award_id))) {
    throw new Error("存在未关联奖项的奖品，请重新添加");
  }
};

const savePayload = (form: LotteryForm): LotteryConfigUpdate => ({
  ...basePayload(form),
  awards: awardPayload(form, false),
  prizes: prizePayload(form),
});

export const saveLotteryConfig = async (activityId: string, form: LotteryForm): Promise<LotteryConfig> => {
  validateForm(form);
  const hasTemporaryAward = form.awards.some(({ award_id }) => typeof award_id === "number" && award_id < 1);
  if (hasTemporaryAward) {
    const awardsOnly = await updateLottery(activityId, {
      ...basePayload(form),
      awards: awardPayload(form, true),
    });
    const savedAwards = new Map(awardsOnly.awards.map((award) => [nameKey(award.name), award.award_id]));
    for (const award of form.awards) {
      if (typeof award.award_id !== "number" || award.award_id > 0) continue;
      const temporaryId = award.award_id;
      const actualId = savedAwards.get(nameKey(award.name));
      if (!actualId) throw new Error(`奖项“${award.name}”保存后未找到对应记录`);
      award.award_id = actualId;
      for (const prize of form.prizes) {
        if (prize.award_id === temporaryId) prize.award_id = actualId;
      }
    }
  }
  return updateLottery(activityId, savePayload(form));
};
