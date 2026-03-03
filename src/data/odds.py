"""
オッズデータ（発走直前最終オッズ）の取得・紐付け。シミュレーションで必須。
"""
from abc import ABC, abstractmethod
from typing import Dict, List

from .schema import HorseEntry


class OddsFetcher(ABC):
    """発走直前最終オッズ取得のインターフェース。"""

    @abstractmethod
    def fetch_final_odds(self, race_id: str) -> Dict[str, float]:
        """
        指定レースの最終オッズを取得する。
        戻り値: entry_id -> オッズ（倍率）の辞書。
        """
        pass


class StubOddsFetcher(OddsFetcher):
    """スタブ実装。実データは取得せず空の辞書を返す。"""

    def fetch_final_odds(self, race_id: str) -> Dict[str, float]:
        return {}


def merge_odds_into_entries(
    entries: List[HorseEntry],
    odds_by_entry_id: Dict[str, float],
) -> List[HorseEntry]:
    """
    出走馬一覧にオッズを紐付ける。
    entry_id をキーに final_odds を設定した新しい HorseEntry のリストを返す。
    """
    result = []
    for e in entries:
        odds = odds_by_entry_id.get(e.entry_id)
        result.append(
            HorseEntry(
                entry_id=e.entry_id,
                race_id=e.race_id,
                frame_number=e.frame_number,
                horse_number=e.horse_number,
                horse_name=e.horse_name,
                previous_order=e.previous_order,
                previous_position_4c=e.previous_position_4c,
                previous_distance=e.previous_distance,
                weight=e.weight,
                final_odds=odds if odds is not None else e.final_odds,
                result_order=e.result_order,
            )
        )
    return result
