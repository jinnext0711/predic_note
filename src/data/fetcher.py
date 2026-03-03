"""
レース・馬データの取得インターフェースとスタブ実装。

データソースが決まり次第、実データ用 Fetcher を実装する。
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from .schema import Race, HorseEntry, RaceWithEntries


class RaceDataFetcher(ABC):
    """レース・馬データ取得のインターフェース。"""

    @abstractmethod
    def fetch_races(
        self,
        start_date: date,
        end_date: date,
        venue: Optional[str] = None,
        surface: Optional[str] = None,
        race_class: Optional[str] = None,
    ) -> List[Race]:
        """条件に合うレース一覧を取得する。"""
        pass

    @abstractmethod
    def fetch_race_entries(self, race_id: str) -> List[HorseEntry]:
        """指定レースの出走馬一覧を取得する。"""
        pass

    def fetch_races_with_entries(
        self,
        start_date: date,
        end_date: date,
        venue: Optional[str] = None,
        surface: Optional[str] = None,
        race_class: Optional[str] = None,
    ) -> List[RaceWithEntries]:
        """レース一覧と各レースの出走馬をまとめて取得する。"""
        races = self.fetch_races(start_date, end_date, venue, surface, race_class)
        result = []
        for race in races:
            entries = self.fetch_race_entries(race.race_id)
            result.append(RaceWithEntries(race=race, entries=entries))
        return result


class StubRaceDataFetcher(RaceDataFetcher):
    """
    スタブ実装。実データは取得せず、空またはサンプルを返す。
    パイプラインの検証・開発用。
    """

    def fetch_races(
        self,
        start_date: date,
        end_date: date,
        venue: Optional[str] = None,
        surface: Optional[str] = None,
        race_class: Optional[str] = None,
    ) -> List[Race]:
        return []

    def fetch_race_entries(self, race_id: str) -> List[HorseEntry]:
        return []
