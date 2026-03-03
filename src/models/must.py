"""
予想ロジック Must モデル。
満たさない馬は除外。ブロック間はAND、同一ブロック内はOR可。異なるカテゴリ間のORは禁止。
"""
from typing import List, Any
from enum import Enum


# Must で使用可能なデータ項目
class MustDataCategory:
    """使用可能データ: 前走着順, 前走4角位置, 前走距離, 斤量, 枠番/馬番, 最終オッズ帯, 血統指標"""
    PREVIOUS_ORDER = "前走着順"
    PREVIOUS_POSITION_4C = "前走4角位置"
    PREVIOUS_DISTANCE = "前走距離"
    WEIGHT = "斤量"
    FRAME_OR_NUMBER = "枠番／馬番"
    FINAL_ODDS_BAND = "最終オッズ帯"
    HORSE_SEX = "馬の性別"
    DAYS_SINCE_LAST_RACE = "前走間隔（日数）"
    BLOODLINE_INDICATOR = "血統指標"


MUST_CATEGORIES_LIST = [
    MustDataCategory.PREVIOUS_ORDER,
    MustDataCategory.PREVIOUS_POSITION_4C,
    MustDataCategory.PREVIOUS_DISTANCE,
    MustDataCategory.WEIGHT,
    MustDataCategory.FRAME_OR_NUMBER,
    MustDataCategory.FINAL_ODDS_BAND,
    MustDataCategory.HORSE_SEX,
    MustDataCategory.DAYS_SINCE_LAST_RACE,
    MustDataCategory.BLOODLINE_INDICATOR,
]

MUST_OPERATORS = [
    ("等しい", "eq"),
    ("以下", "le"),
    ("以上", "ge"),
    ("未満", "lt"),
    ("より大きい", "gt"),
    ("含む", "in"),
]


class MustBlock:
    """Must の1ブロック。同一ブロック内はORで複数条件。"""

    def __init__(self, conditions: List[dict]):
        # conditions: [{"category": str, "operator": str, "value": Any}, ...]
        self.conditions = list(conditions) if conditions else []

    def is_valid(self) -> bool:
        return bool(self.conditions)

    def to_dict(self) -> dict:
        return {"conditions": self.conditions}

    @classmethod
    def from_dict(cls, d: dict) -> "MustBlock":
        return cls(conditions=d.get("conditions", []))


class MustLogic:
    """Must ロジック全体。ブロック間はAND。"""

    def __init__(self, blocks: List[MustBlock]):
        self.blocks = list(blocks) if blocks else []

    def is_valid(self) -> bool:
        return all(b.is_valid() for b in self.blocks)

    def to_dict(self) -> dict:
        return {"blocks": [b.to_dict() for b in self.blocks]}

    @classmethod
    def from_dict(cls, d: dict) -> "MustLogic":
        blocks = [MustBlock.from_dict(b) for b in d.get("blocks", [])]
        return cls(blocks=blocks)
