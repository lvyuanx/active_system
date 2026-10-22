import { describe, expect, it } from "vitest";
import { apiURL, lotteryWebSocketURL, mediaURL } from "../src/utils/http";
import { setRuntimeConfigFromOrigin } from "../src/config";
import { parseActivityId, parseActivityIdFromScanValue, parseScanTarget } from "../src/utils/launch";
import { activityTokenKey } from "../src/utils/storage";
import { isAgreementVersionAccepted, userAgreementVersion } from "../src/utils/privacy";
import { mergeChatMessages, messageAvatarId } from "../src/utils/chat";
import { applySnapshotToControl, drawsForPrize, flattenPrizes } from "../src/utils/lottery";
import { ChatMessage, MobileLotterySnapshot } from "../src/types/api";

const message = (id: number, body: string): ChatMessage => ({
  message_id: id,
  activity_id: "activity-1",
  sender_activity_user_id: id,
  sender_username: `用户${id}`,
  body,
  created_at: "2026-01-01T10:00:00Z",
  message_type: "text",
  sticker: null,
});

describe("小程序活动入口和请求地址", () => {
  it("解析直接启动参数和扫码 scene", () => {
    expect(parseActivityId({ query: { activity_id: "activity-1" } })).toBe("activity-1");
    expect(parseActivityId({ query: { scene: "activity_id%3Dactivity-2" } })).toBe("activity-2");
    expect(parseActivityId({ query: {} })).toBeUndefined();
  });

  it("解析管理员生成的 Web 活动二维码 URL", () => {
    expect(parseActivityIdFromScanValue("https://example.com/user/activity/activity-3")).toBe("activity-3");
    expect(parseActivityIdFromScanValue("https://example.com/user/?activity_id=activity-4")).toBe("activity-4");
    expect(parseActivityIdFromScanValue("https://example.com/user/activity/unknown?q=1")).toBe("unknown");
    expect(parseScanTarget("https://example.com/user/activity/activity-5")).toEqual({
      activityId: "activity-5",
      origin: "https://example.com",
    });
  });

  it("按活动隔离 token key，并生成 API、WS 和媒体地址", () => {
    expect(activityTokenKey("a")).toBe("active_user_token:a");
    expect(apiURL("/activities/a")).toBe("http://localhost:8000/api/v1/activities/a");
    expect(lotteryWebSocketURL("a")).toBe("ws://localhost:8000/api/v1/activities/a/lottery/ws");
    expect(mediaURL("/api/v1/activities/a/lottery/prizes/1/image?v=x")).toBe(
      "http://localhost:8000/api/v1/activities/a/lottery/prizes/1/image?v=x",
    );
  });

  it("不从本地开发二维码覆盖 API 端口", () => {
    expect(setRuntimeConfigFromOrigin("http://localhost:5175")).toBe(false);
    expect(setRuntimeConfigFromOrigin("https://public.example.com")).toBe(true);
  });
});

describe("用户协议同意状态", () => {
  it("只接受当前版本的本地同意记录", () => {
    expect(isAgreementVersionAccepted({ version: userAgreementVersion })).toBe(true);
    expect(isAgreementVersionAccepted({ version: "2026-01-01" })).toBe(false);
    expect(isAgreementVersionAccepted(undefined)).toBe(false);
  });
});

describe("聊天消息逻辑", () => {
  it("按 message_id 去重并保持时间顺序", () => {
    expect(mergeChatMessages([message(2, "旧")], [message(1, "更早"), message(2, "更新")]))
      .toEqual([message(1, "更早"), message(2, "更新")]);
  });

  it("为当前用户使用持久化头像，为其他用户使用稳定映射", () => {
    expect(messageAvatarId(message(7, "self"), 7, 12)).toBe(12);
    expect(messageAvatarId(message(21, "other"), 7, 12)).toBe(1);
  });
});

describe("抽奖快照逻辑", () => {
  const snapshot: MobileLotterySnapshot = {
    activity_id: "activity-1",
    activity_name: "测试活动",
    activity_status: "open",
    config: { no_repeat_across_prizes: false, rolling_name_count: 8 },
    awards: [{
      award_id: 1,
      name: "一等奖",
      sort_order: 1,
      prizes: [{
        prize_id: 1,
        award_id: 1,
        name: "礼品",
        quantity: 2,
        remaining_quantity: 2,
        sort_order: 1,
        is_enabled: true,
        image_url: null,
      }],
      draws: [],
    }],
    draws: [],
    latest_draw_id: 0,
    selected_prize_id: 1,
    active_round: null,
  };

  it("只展开启用奖品并筛选当前奖品中奖人", () => {
    expect(flattenPrizes(snapshot.awards)).toHaveLength(1);
    expect(drawsForPrize([], 1)).toEqual([]);
  });

  it("恢复进行中的抽奖阶段", () => {
    const state = applySnapshotToControl({
      ...snapshot,
      active_round: {
        round_id: "round-1",
        award_id: 1,
        award_name: "一等奖",
        prize_id: 1,
        prize_name: "礼品",
        phase: "stopping",
        participants: [],
        started_at: "2026-01-01T10:00:00Z",
      },
    });
    expect(state.phase).toBe("stopping");
    expect(state.pendingRoundId).toBe("round-1");
  });
});
