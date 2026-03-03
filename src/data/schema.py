"""
レース・馬データのスキーマ定義（MVP 対象範囲に準拠）。

対象: 中央競馬・過去5年・平地・未勝利戦以上・新馬戦除外。
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List


@dataclass
class Race:
    """1レースのメタデータ。"""

    race_id: str
    date: date
    venue: str  # 競馬場（Scope の VENUES に準拠）
    distance: int  # 距離（m）
    surface: str  # 芝 / ダート
    race_class: str  # クラス（未勝利, 1勝, ...）
    age_condition: str  # 年齢条件（2歳, 3歳, ...）
    race_name: Optional[str] = None
    number_of_entries: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "date": self.date.isoformat(),
            "venue": self.venue,
            "distance": self.distance,
            "surface": self.surface,
            "race_class": self.race_class,
            "age_condition": self.age_condition,
            "race_name": self.race_name,
            "number_of_entries": self.number_of_entries,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Race":
        return cls(
            race_id=d["race_id"],
            date=date.fromisoformat(d["date"]),
            venue=d["venue"],
            distance=int(d["distance"]),
            surface=d["surface"],
            race_class=d["race_class"],
            age_condition=d["age_condition"],
            race_name=d.get("race_name"),
            number_of_entries=d.get("number_of_entries"),
        )


@dataclass
class HorseEntry:
    """1頭の出走情報（レース単位）。Must で使う項目を含む。"""

    entry_id: str  # レース内で一意（例: race_id + 馬番）
    race_id: str
    frame_number: int  # 枠番
    horse_number: int  # 馬番
    horse_name: str
    # 前走系（Must で使用可能）
    previous_order: Optional[int] = None  # 前走着順
    previous_position_4c: Optional[int] = None  # 前走4角位置
    previous_distance: Optional[int] = None  # 前走距離（m）
    weight: Optional[float] = None  # 斤量
    final_odds: Optional[float] = None  # 最終オッズ
    result_order: Optional[int] = None  # 着順（結果が出ている場合）
    horse_sex: Optional[str] = None  # 馬の性別（牡/牝/セ）
    days_since_last_race: Optional[int] = None  # 前走からの間隔（日数）

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "race_id": self.race_id,
            "frame_number": self.frame_number,
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "previous_order": self.previous_order,
            "previous_position_4c": self.previous_position_4c,
            "previous_distance": self.previous_distance,
            "weight": self.weight,
            "final_odds": self.final_odds,
            "result_order": self.result_order,
            "horse_sex": self.horse_sex,
            "days_since_last_race": self.days_since_last_race,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HorseEntry":
        return cls(
            entry_id=d["entry_id"],
            race_id=d["race_id"],
            frame_number=int(d["frame_number"]),
            horse_number=int(d["horse_number"]),
            horse_name=d["horse_name"],
            previous_order=d.get("previous_order"),
            previous_position_4c=d.get("previous_position_4c"),
            previous_distance=d.get("previous_distance"),
            weight=float(d["weight"]) if d.get("weight") is not None else None,
            final_odds=float(d["final_odds"]) if d.get("final_odds") is not None else None,
            result_order=d.get("result_order"),
            horse_sex=d.get("horse_sex"),
            days_since_last_race=int(d["days_since_last_race"]) if d.get("days_since_last_race") is not None else None,
        )


@dataclass
class RaceWithEntries:
    """レースとその出走馬一覧。"""

    race: Race
    entries: List[HorseEntry] = field(default_factory=list)
