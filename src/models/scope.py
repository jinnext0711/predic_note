"""
レース要件（Scope）モデル。
対象レースを定義。予想ロジックではない。ブロック間はAND、同一カテゴリ内のみOR可。
"""
from typing import List, Optional
from enum import Enum


class ScopeBlock:
    """1カテゴリ分の条件（同一カテゴリ内はORで複数選択可）。"""

    def __init__(self, category: str, selected_values: List[str]):
        self.category = category  # 競馬場, 芝/ダート, クラス, 年齢条件
        self.selected_values = selected_values  # 選択された値（OR）

    def is_valid(self) -> bool:
        """必須入力: 各カテゴリで少なくとも1つ選択されていること。"""
        return bool(self.selected_values)


class RaceScope:
    """レース要件全体。全ブロック必須・ブロック間はAND。"""

    def __init__(
        self,
        venues: List[str],
        surface: List[str],  # 芝/ダート
        race_class: List[str],
        age_condition: List[str],
        distance_min: Optional[int] = None,  # 距離下限（m）
        distance_max: Optional[int] = None,  # 距離上限（m）
        # 後方互換: 旧カテゴリ形式を受け取れるようにする（内部では使わない）
        distances: List[str] = None,
    ):
        self.venues = venues
        self.surface = surface
        self.race_class = race_class
        self.age_condition = age_condition
        self.distance_min = distance_min
        self.distance_max = distance_max

    def is_valid(self) -> bool:
        """全カテゴリで少なくとも1つずつ選択されていること + 距離範囲が設定されていること。"""
        has_distance = (self.distance_min is not None and self.distance_max is not None)
        return all([
            bool(self.venues),
            has_distance,
            bool(self.surface),
            bool(self.race_class),
            bool(self.age_condition),
        ])

    def to_dict(self) -> dict:
        return {
            "venues": self.venues,
            "distance_min": self.distance_min,
            "distance_max": self.distance_max,
            "surface": self.surface,
            "race_class": self.race_class,
            "age_condition": self.age_condition,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RaceScope":
        distance_min = d.get("distance_min")
        distance_max = d.get("distance_max")

        # 旧形式（distances カテゴリリスト）からの自動変換
        if distance_min is None and distance_max is None and d.get("distances"):
            distance_min, distance_max = _convert_categories_to_range(d["distances"])

        return cls(
            venues=d.get("venues", []),
            surface=d.get("surface", []),
            race_class=d.get("race_class", []),
            age_condition=d.get("age_condition", []),
            distance_min=int(distance_min) if distance_min is not None else None,
            distance_max=int(distance_max) if distance_max is not None else None,
        )


# 旧カテゴリ → 距離範囲の変換テーブル
_CATEGORY_RANGES = {
    "短距離": (1000, 1400),
    "マイル": (1401, 1800),
    "中距離": (1801, 2400),
    "長距離": (2401, 3600),
}


def _convert_categories_to_range(categories: List[str]) -> tuple:
    """旧距離カテゴリリストから(min, max)を算出する。"""
    all_min = []
    all_max = []
    for cat in categories:
        lo, hi = _CATEGORY_RANGES.get(cat, (1000, 3600))
        all_min.append(lo)
        all_max.append(hi)
    if not all_min:
        return (1000, 3600)
    return (min(all_min), max(all_max))
