"""
レース・馬データの取得→保存パイプライン（タスク 1.1, 1.2）。

Fetcher で取得し、storage で data/ に保存。オッズは OddsFetcher で取得・紐付け。
"""
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from .fetcher import RaceDataFetcher, StubRaceDataFetcher
from .odds import OddsFetcher, StubOddsFetcher, merge_odds_into_entries
from .schema import Race, HorseEntry, RaceWithEntries
from . import storage

logger = logging.getLogger(__name__)

# バッチ保存の単位（この件数ごとにディスクに保存）
BATCH_SAVE_SIZE = 10


def run_fetch_and_save(
    start_date: date,
    end_date: date,
    fetcher: Optional[RaceDataFetcher] = None,
    base_path: Optional[Path] = None,
    venue: Optional[str] = None,
    surface: Optional[str] = None,
    race_class: Optional[str] = None,
) -> int:
    """
    指定期間のレースを取得し、data/ に保存する。
    中断しても取得済み分は保存済み（バッチ保存）。
    戻り値: 保存したレース数。
    """
    if fetcher is None:
        fetcher = StubRaceDataFetcher()
    races = fetcher.fetch_races(start_date, end_date, venue, surface, race_class)
    if not races:
        return 0

    # 1レースずつ即座に保存（中断耐性・リアルタイム進捗）
    saved = 0
    for race in races:
        entries = fetcher.fetch_race_entries(race.race_id)
        if entries:
            storage.save_entries(race.race_id, entries, base_path)
        storage.save_races([race], base_path)
        saved += 1

        if saved % 10 == 0:
            logger.info("保存済み: %d / %d レース", saved, len(races))

    logger.info("完了: %d レース保存", saved)
    return saved


def run_fetch_past_5_years(
    fetcher: Optional[RaceDataFetcher] = None,
    base_path: Optional[Path] = None,
) -> int:
    """過去5年分を取得する（MVP データ期間）。スタブの場合は 0 件。"""
    end = date.today()
    start = end - timedelta(days=5 * 365)
    return run_fetch_and_save(start, end, fetcher=fetcher, base_path=base_path)


def run_fetch_odds_and_merge(
    odds_fetcher: Optional[OddsFetcher] = None,
    base_path: Optional[Path] = None,
) -> int:
    """
    保存済みレースの出走馬に対してオッズを取得し、紐付けて保存する（タスク 1.2）。
    戻り値: オッズを更新したレース数。
    """
    if odds_fetcher is None:
        odds_fetcher = StubOddsFetcher()
    races = storage.load_races(base_path)
    updated = 0
    for race in races:
        entries = storage.load_entries(race.race_id, base_path)
        if not entries:
            continue
        odds_by_entry = odds_fetcher.fetch_final_odds(race.race_id)
        if not odds_by_entry:
            continue
        merged = merge_odds_into_entries(entries, odds_by_entry)
        storage.save_entries(race.race_id, merged, base_path)
        updated += 1
    return updated
