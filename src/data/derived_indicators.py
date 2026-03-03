"""
導出指標の算出（MVP最小セット）。

対象指標:
  - 逃げ馬数: レース単位で前走4角位置が1〜2位の馬の数
  - 先行馬数: レース単位で前走4角位置が3〜4位の馬の数
  - 前走位置平均との差: 馬ごとに、そのレースの前走4角位置平均との差
  - レースペース簡易分類: 逃げ・先行馬の割合に基づく速/普/遅

前走4角位置の定義:
  - 逃げ: previous_position_4c が 1〜2
  - 先行: previous_position_4c が 3〜4
"""
from dataclasses import dataclass
from typing import List, Optional

from .schema import HorseEntry


@dataclass
class RaceDerivedIndicators:
    """レース単位の導出指標。"""

    race_id: str
    nige_count: int  # 逃げ馬数
    senko_count: int  # 先行馬数
    avg_position_4c: Optional[float]  # レース全体の前走4角位置平均
    pace_class: str  # レースペース簡易分類（速/普/遅）


@dataclass
class HorseDerivedIndicators:
    """馬単位の導出指標。"""

    entry_id: str
    diff_from_avg_position_4c: Optional[float]  # 前走位置平均との差


def count_nige(entries: List[HorseEntry]) -> int:
    """逃げ馬数を算出する。前走4角位置が1〜2の馬。"""
    return sum(
        1 for e in entries
        if e.previous_position_4c is not None and e.previous_position_4c <= 2
    )


def count_senko(entries: List[HorseEntry]) -> int:
    """先行馬数を算出する。前走4角位置が3〜4の馬。"""
    return sum(
        1 for e in entries
        if e.previous_position_4c is not None and e.previous_position_4c in (3, 4)
    )


def calc_avg_position_4c(entries: List[HorseEntry]) -> Optional[float]:
    """レース全体の前走4角位置平均を算出する。データがなければ None。"""
    positions = [
        e.previous_position_4c for e in entries
        if e.previous_position_4c is not None
    ]
    if not positions:
        return None
    return sum(positions) / len(positions)


def calc_diff_from_avg(
    entry: HorseEntry,
    avg_position_4c: Optional[float],
) -> Optional[float]:
    """馬ごとの前走4角位置平均との差を算出する。正=後方寄り、負=前方寄り。"""
    if entry.previous_position_4c is None or avg_position_4c is None:
        return None
    return entry.previous_position_4c - avg_position_4c


def classify_pace(entries: List[HorseEntry]) -> str:
    """
    レースペース簡易分類。逃げ・先行馬の割合で速/普/遅を判定する。

    判定基準:
      - 前走4角位置データがある馬のうち、逃げ+先行（4角位置1〜4）の割合を算出
      - 40%超 → 速
      - 20%未満 → 遅
      - それ以外 → 普
      - データ不足（前走4角位置を持つ馬が0頭）→ 普
    """
    entries_with_data = [
        e for e in entries if e.previous_position_4c is not None
    ]
    if not entries_with_data:
        return "普"
    front_count = sum(
        1 for e in entries_with_data if e.previous_position_4c <= 4
    )
    ratio = front_count / len(entries_with_data)
    if ratio > 0.4:
        return "速"
    elif ratio < 0.2:
        return "遅"
    return "普"


def compute_race_indicators(
    race_id: str,
    entries: List[HorseEntry],
) -> RaceDerivedIndicators:
    """レース単位の導出指標をまとめて算出する。"""
    return RaceDerivedIndicators(
        race_id=race_id,
        nige_count=count_nige(entries),
        senko_count=count_senko(entries),
        avg_position_4c=calc_avg_position_4c(entries),
        pace_class=classify_pace(entries),
    )


def compute_horse_indicators(
    entries: List[HorseEntry],
    avg_position_4c: Optional[float],
) -> List[HorseDerivedIndicators]:
    """馬単位の導出指標をまとめて算出する。"""
    return [
        HorseDerivedIndicators(
            entry_id=e.entry_id,
            diff_from_avg_position_4c=calc_diff_from_avg(e, avg_position_4c),
        )
        for e in entries
    ]


def compute_all(
    race_id: str,
    entries: List[HorseEntry],
) -> tuple:
    """
    レース・馬すべての導出指標を算出する。

    戻り値: (RaceDerivedIndicators, List[HorseDerivedIndicators])

    使用例（pipeline.py との統合ポイント）:
        entries = storage.load_entries(race_id)
        race_ind, horse_inds = compute_all(race_id, entries)
    """
    race_ind = compute_race_indicators(race_id, entries)
    horse_inds = compute_horse_indicators(entries, race_ind.avg_position_4c)
    return race_ind, horse_inds
