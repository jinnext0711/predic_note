"""
netkeiba_fetcher のテスト。

HTTPリクエストはモックし、パイプラインロジックのみテストする。
"""
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.data.netkeiba_fetcher import (
    NetkeibaRaceDataFetcher,
    _generate_dates,
)
from src.data.schema import Race, HorseEntry


class TestGenerateDates:
    def test_single_day(self):
        dates = _generate_dates(date(2024, 1, 1), date(2024, 1, 1))
        assert len(dates) == 1
        assert dates[0] == date(2024, 1, 1)

    def test_range(self):
        dates = _generate_dates(date(2024, 1, 1), date(2024, 1, 3))
        assert len(dates) == 3

    def test_end_before_start(self):
        dates = _generate_dates(date(2024, 1, 3), date(2024, 1, 1))
        assert len(dates) == 0


class TestNetkeibaFetcher:
    def test_interval_minimum(self):
        """間隔は最低2秒"""
        fetcher = NetkeibaRaceDataFetcher(interval=0.5)
        assert fetcher._interval == 2.0

    def test_interval_default(self):
        fetcher = NetkeibaRaceDataFetcher()
        assert fetcher._interval == 3.0

    def test_skip_existing(self, tmp_path):
        """取得済みレースはスキップされる"""
        from src.data import storage

        # 既存レースを保存
        existing_race = Race(
            race_id="202406010101",
            date=date(2024, 1, 6),
            venue="中山",
            distance=1200,
            surface="ダート",
            race_class="未勝利",
            age_condition="3歳",
        )
        storage.save_races([existing_race], tmp_path)

        fetcher = NetkeibaRaceDataFetcher(
            base_path=tmp_path,
            skip_existing=True,
        )
        assert fetcher._is_existing("202406010101") is True
        assert fetcher._is_existing("202406010199") is False

    def test_no_skip(self, tmp_path):
        """skip_existing=False で既存もスキップしない"""
        from src.data import storage

        existing_race = Race(
            race_id="202406010101",
            date=date(2024, 1, 6),
            venue="中山",
            distance=1200,
            surface="ダート",
            race_class="未勝利",
            age_condition="3歳",
        )
        storage.save_races([existing_race], tmp_path)

        fetcher = NetkeibaRaceDataFetcher(
            base_path=tmp_path,
            skip_existing=False,
        )
        assert fetcher._is_existing("202406010101") is False

    @patch.object(NetkeibaRaceDataFetcher, "_get")
    def test_fetch_race_ids_for_date(self, mock_get):
        """日付別レースID取得"""
        mock_get.return_value = """
        <html><body>
        <a href="/race/202406010101/">Test</a>
        <a href="/race/202406010102/">Test2</a>
        </body></html>
        """
        fetcher = NetkeibaRaceDataFetcher(skip_existing=False)
        ids = fetcher.fetch_race_ids_for_date(date(2024, 1, 6))
        assert len(ids) == 2
        assert "202406010101" in ids

    @patch.object(NetkeibaRaceDataFetcher, "_get")
    def test_fetch_race_ids_failure(self, mock_get):
        """HTTPエラー時は空リスト"""
        mock_get.return_value = None
        fetcher = NetkeibaRaceDataFetcher(skip_existing=False)
        ids = fetcher.fetch_race_ids_for_date(date(2024, 1, 6))
        assert ids == []

    def test_entries_cache(self):
        """fetch_racesで取得したエントリーがキャッシュされる"""
        fetcher = NetkeibaRaceDataFetcher(skip_existing=False)
        entry = HorseEntry(
            entry_id="test_01",
            race_id="test",
            frame_number=1,
            horse_number=1,
            horse_name="テスト",
        )
        fetcher._last_entries_cache["test"] = [entry]

        # キャッシュから取得
        entries = fetcher.fetch_race_entries("test")
        assert len(entries) == 1
        assert entries[0].horse_name == "テスト"

        # キャッシュはクリアされる
        assert "test" not in fetcher._last_entries_cache
