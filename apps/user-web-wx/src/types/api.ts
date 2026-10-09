export type ActivityStatus = "closed" | "open" | "ended";

export type ActivityAvatarId =
  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10
  | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20;

export interface Activity {
  activity_id: string;
  name: string;
  description: string | null;
  status: ActivityStatus;
}

export interface ActivityUserResponse {
  access_token: string;
  token_type: string;
  activity_id: string;
  activity_user_id: number;
  username: string;
  joined_at: string;
  avatar_id: ActivityAvatarId;
  can_mobile_lottery: boolean;
}

export interface SmsCodeSendResponse {
  message: string;
  expires_in: number;
  retry_after: number;
}

export interface SmsLoginResponse {
  needs_name: boolean;
  user: ActivityUserResponse | null;
  verification_token: string | null;
}

export interface ChatSticker {
  sticker_id: number;
  name: string;
  image_url: string;
  mime: string;
  width: number;
  height: number;
}

export interface ChatMessage {
  message_id: number;
  activity_id: string;
  sender_activity_user_id: number;
  sender_username: string;
  body: string;
  created_at: string;
  message_type: "text" | "sticker";
  sticker: ChatSticker | null;
}

export interface ChatMessagePage {
  items: ChatMessage[];
  has_more: boolean;
}

export interface MobileLotteryPrize {
  prize_id: number;
  award_id: number;
  name: string;
  quantity: number;
  remaining_quantity: number;
  sort_order: number;
  is_enabled: boolean;
  image_url: string | null;
}

export interface MobileLotteryDraw {
  draw_id: number;
  activity_id: string;
  award_id: number;
  prize_id: number;
  award_name: string;
  prize_name: string;
  draw_number: number;
  remaining_quantity: number;
  prize_image_url: string | null;
  winner: { activity_user_id: number; username: string; avatar_id: number };
  drawn_at: string;
}

export interface MobileLotteryAward {
  award_id: number;
  name: string;
  sort_order: number;
  prizes: MobileLotteryPrize[];
  draws: MobileLotteryDraw[];
}

export interface MobileLotteryRoundParticipant {
  activity_user_id: number;
  username: string;
  avatar_id: number;
}

export interface MobileLotteryRound {
  round_id: string;
  award_id: number;
  award_name: string;
  prize_id: number;
  prize_name: string;
  phase: "rolling" | "stopping";
  participants: MobileLotteryRoundParticipant[];
  started_at: string;
}

export interface MobileLotterySnapshot {
  activity_id: string;
  activity_name: string;
  activity_status: ActivityStatus;
  config: { no_repeat_across_prizes: boolean; rolling_name_count: number };
  awards: MobileLotteryAward[];
  draws: MobileLotteryDraw[];
  latest_draw_id: number;
  selected_prize_id: number | null;
  active_round: MobileLotteryRound | null;
}

export type LotterySocketPayload = Record<string, unknown>;
