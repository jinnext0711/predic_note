"""
マーケットプレイス出品データモデル。
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MarketplaceListing:
    """マーケットプレイスに出品されたアルゴリズム。"""

    logic_key: str          # "owner::name"
    seller: str             # 出品者名
    price: int              # ポイント価格
    description_short: str  # 短い説明（ロジック詳細は非公開）
    listed_at: str          # 出品日時 ISO形式
    # バックテストキャッシュ（出品時に自動計算）
    backtest_win: Dict = field(default_factory=dict)    # {"試行回数": N, "的中率": X, "回収率": Y}
    backtest_place: Dict = field(default_factory=dict)  # 同上（複勝）
    purchase_count: int = 0

    def to_dict(self) -> dict:
        return {
            "seller": self.seller,
            "price": self.price,
            "description_short": self.description_short,
            "listed_at": self.listed_at,
            "backtest_win": self.backtest_win,
            "backtest_place": self.backtest_place,
            "purchase_count": self.purchase_count,
        }

    @classmethod
    def from_dict(cls, logic_key: str, d: dict) -> "MarketplaceListing":
        return cls(
            logic_key=logic_key,
            seller=d.get("seller", ""),
            price=int(d.get("price", 0)),
            description_short=d.get("description_short", ""),
            listed_at=d.get("listed_at", ""),
            backtest_win=d.get("backtest_win", {}),
            backtest_place=d.get("backtest_place", {}),
            purchase_count=int(d.get("purchase_count", 0)),
        )
