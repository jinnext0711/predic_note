"""
予想結果データモデル。
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PredictionResult:
    """予想実行の結果。"""

    logic_name: str
    logic_owner: str
    race_info: Dict = field(default_factory=dict)  # {venue, distance, surface, ...}
    pick_horse_name: str = ""
    pick_horse_number: int = 0
    bet_type: str = "単勝"           # "単勝" / "複勝"
    predicted_at: str = ""           # 予想実行日時 ISO形式
    # ロジック成績（参考値）
    backtest_hit_rate: float = 0.0
    backtest_recovery_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "logic_name": self.logic_name,
            "logic_owner": self.logic_owner,
            "race_info": self.race_info,
            "pick_horse_name": self.pick_horse_name,
            "pick_horse_number": self.pick_horse_number,
            "bet_type": self.bet_type,
            "predicted_at": self.predicted_at,
            "backtest_hit_rate": self.backtest_hit_rate,
            "backtest_recovery_rate": self.backtest_recovery_rate,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PredictionResult":
        return cls(
            logic_name=d.get("logic_name", ""),
            logic_owner=d.get("logic_owner", ""),
            race_info=d.get("race_info", {}),
            pick_horse_name=d.get("pick_horse_name", ""),
            pick_horse_number=int(d.get("pick_horse_number", 0)),
            bet_type=d.get("bet_type", "単勝"),
            predicted_at=d.get("predicted_at", ""),
            backtest_hit_rate=float(d.get("backtest_hit_rate", 0.0)),
            backtest_recovery_rate=float(d.get("backtest_recovery_rate", 0.0)),
        )
