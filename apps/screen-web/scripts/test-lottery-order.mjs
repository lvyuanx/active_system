import assert from "node:assert/strict";
import { enqueueLotteryDraw, readyLotteryDrawIds } from "../dist-test/lottery/lottery-order.js";

const draw = (draw_id) => ({
  draw_id,
  activity_id: "activity",
  award_id: 1,
  prize_id: 1,
  award_name: "三等奖",
  prize_name: "耳机",
  draw_number: draw_id,
  remaining_quantity: 1,
  winner: { activity_user_id: draw_id, username: `用户${draw_id}` },
  drawn_at: "2026-08-28T00:00:00+00:00",
});
const known = readyLotteryDrawIds([draw(10)]);
let queue = [];
queue = enqueueLotteryDraw(known, queue, draw(12));
queue = enqueueLotteryDraw(known, queue, draw(11));
queue = enqueueLotteryDraw(known, queue, draw(12));
queue = enqueueLotteryDraw(known, queue, draw(10));
assert.deepEqual(queue.map((item) => item.draw_id), [11, 12]);
assert.equal(known.has(10), true);
assert.equal(known.has(11), true);
assert.equal(known.has(12), true);
console.log("lottery order tests passed");
