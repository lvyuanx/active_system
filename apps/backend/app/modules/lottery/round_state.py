from dataclasses import dataclass, replace
from datetime import datetime
from threading import RLock
from typing import Any, Literal

from .models import LotteryRoundParticipant, LotteryRoundPublic


@dataclass(frozen=True)
class LotteryRound:
    activity_id: str
    round_id: str
    award_id: int
    award_name: str
    prize_id: int
    prize_name: str
    participants: tuple[LotteryRoundParticipant, ...]
    candidate_user_ids: frozenset[int]
    started_at: datetime
    phase: Literal["rolling", "stopping"] = "rolling"

    @property
    def public(self) -> LotteryRoundPublic:
        return LotteryRoundPublic(
            round_id=self.round_id,
            award_id=self.award_id,
            award_name=self.award_name,
            prize_id=self.prize_id,
            prize_name=self.prize_name,
            participants=list(self.participants),
            started_at=self.started_at,
            phase=self.phase,
        )

    def public_payload(self) -> dict[str, Any]:
        return self.public.model_dump(mode="json")


class LotteryRoundStore:
    """维护单进程活动轮次；进程重启时未落库轮次自然取消。"""

    def __init__(self) -> None:
        self._rounds: dict[str, LotteryRound] = {}
        self._lock = RLock()

    def get(self, activity_id: str) -> LotteryRound | None:
        with self._lock:
            return self._rounds.get(activity_id)

    def put_if_absent(self, lottery_round: LotteryRound) -> bool:
        with self._lock:
            if lottery_round.activity_id in self._rounds:
                return False
            self._rounds[lottery_round.activity_id] = lottery_round
            return True

    def clear_if(self, activity_id: str, round_id: str) -> bool:
        with self._lock:
            current = self._rounds.get(activity_id)
            if current is None or current.round_id != round_id:
                return False
            del self._rounds[activity_id]
            return True

    def mark_stopping(self, activity_id: str, round_id: str) -> LotteryRound | None:
        with self._lock:
            current = self._rounds.get(activity_id)
            if current is None or current.round_id != round_id:
                return None
            if current.phase == "stopping":
                return current
            updated = replace(current, phase="stopping")
            self._rounds[activity_id] = updated
            return updated

    def clear_all(self) -> None:
        with self._lock:
            self._rounds.clear()


class LotterySelectionStore:
    """保存活动当前选中的奖品，供管理端切换和大屏重连恢复使用。"""

    def __init__(self) -> None:
        self._selected_prizes: dict[str, int] = {}
        self._lock = RLock()

    def get(self, activity_id: str) -> int | None:
        with self._lock:
            return self._selected_prizes.get(activity_id)

    def set(self, activity_id: str, prize_id: int) -> None:
        with self._lock:
            self._selected_prizes[activity_id] = prize_id

    def clear_all(self) -> None:
        with self._lock:
            self._selected_prizes.clear()


lottery_round_store = LotteryRoundStore()
lottery_selection_store = LotterySelectionStore()
