"""
フォワード成績の記録モデル（タスク 5.2）。

実運用での予想結果（的中/不的中・払戻金額）を1レースずつ記録する。
シミュレーション不可ロジックも含め、全ロジックで利用可能（無料機能）。
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ForwardResult:
    """1レースの予想結果。"""

    race_id: str
    race_date: str  # YYYY-MM-DD
    race_name: Optional[str]  # レース名（表示用）
    bet_type: str  # 単勝 / 複勝
    horse_name: str  # 予想した馬名
    horse_number: Optional[int]  # 馬番
    bet_amount: int  # 賭け金（円）
    is_hit: bool  # 的中したか
    payout: float  # 払戻金額（不的中なら0）

    def profit(self) -> float:
        """損益を返す。"""
        return self.payout - self.bet_amount

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_date": self.race_date,
            "race_name": self.race_name,
            "bet_type": self.bet_type,
            "horse_name": self.horse_name,
            "horse_number": self.horse_number,
            "bet_amount": self.bet_amount,
            "is_hit": self.is_hit,
            "payout": self.payout,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ForwardResult":
        return cls(
            race_id=d["race_id"],
            race_date=d["race_date"],
            race_name=d.get("race_name"),
            bet_type=d.get("bet_type", "単勝"),
            horse_name=d.get("horse_name", ""),
            horse_number=d.get("horse_number"),
            bet_amount=int(d.get("bet_amount", 100)),
            is_hit=bool(d.get("is_hit", False)),
            payout=float(d.get("payout", 0)),
        )


@dataclass
class ForwardRecord:
    """1ロジックのフォワード成績（結果一覧）。"""

    logic_name: str
    results: List[ForwardResult] = field(default_factory=list)

    def total_trials(self) -> int:
        """試行回数。"""
        return len(self.results)

    def total_hits(self) -> int:
        """的中数。"""
        return sum(1 for r in self.results if r.is_hit)

    def hit_rate(self) -> float:
        """的中率（%）。"""
        if not self.results:
            return 0.0
        return self.total_hits() / len(self.results) * 100

    def total_bet(self) -> int:
        """総投資額。"""
        return sum(r.bet_amount for r in self.results)

    def total_payout(self) -> float:
        """総回収額。"""
        return sum(r.payout for r in self.results)

    def recovery_rate(self) -> float:
        """回収率（%）。"""
        tb = self.total_bet()
        if tb == 0:
            return 0.0
        return self.total_payout() / tb * 100

    def total_profit(self) -> float:
        """総損益。"""
        return self.total_payout() - self.total_bet()

    def to_dict(self) -> dict:
        return {
            "logic_name": self.logic_name,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ForwardRecord":
        return cls(
            logic_name=d.get("logic_name", ""),
            results=[ForwardResult.from_dict(r) for r in d.get("results", [])],
        )
