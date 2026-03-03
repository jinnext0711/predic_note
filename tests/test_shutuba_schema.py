"""
出馬表スキーマ (shutuba_schema.py) のテスト。

全データクラスの to_dict() / from_dict() ラウンドトリップ、
エッジケース（None値、空リスト）、データ整合性を検証する。
"""
import pytest

from data.shutuba_schema import (
    HorseHistory,
    JockeyStats,
    OddsData,
    PastRaceRecord,
    TrainerStats,
    UpcomingHorseEntry,
    UpcomingRaceWithEntries,
)


# ---------------------------------------------------------------------------
# ヘルパー関数: サンプルデータ生成
# ---------------------------------------------------------------------------


def _make_entry(
    horse_number: int = 1,
    horse_name: str = "テスト馬",
    race_id: str = "202501010101",
    morning_odds: float = None,
    popularity: int = None,
    horse_weight: str = None,
) -> UpcomingHorseEntry:
    """テスト用 UpcomingHorseEntry を生成する。"""
    return UpcomingHorseEntry(
        entry_id=f"{race_id}_{horse_number:02d}",
        race_id=race_id,
        frame_number=(horse_number + 1) // 2,
        horse_number=horse_number,
        horse_name=horse_name,
        horse_id=f"horse_{horse_number:04d}",
        sex_age="牡3",
        weight_carry=57.0,
        jockey_name="テスト騎手",
        jockey_id=f"jockey_{horse_number:04d}",
        trainer_name="テスト調教師",
        trainer_id=f"trainer_{horse_number:04d}",
        horse_weight=horse_weight,
        morning_odds=morning_odds,
        popularity=popularity,
    )


def _make_past_record(**overrides) -> PastRaceRecord:
    """テスト用 PastRaceRecord を生成する。"""
    defaults = dict(
        race_date="2025-01-01",
        venue="中山",
        race_name="テストレース",
        surface="芝",
        distance=2000,
        weather="晴",
        track_condition="良",
        horse_number=1,
        result_order=3,
        time_str="2:01.5",
        last_3f=34.8,
        odds=5.0,
        popularity=2,
        weight_carry=57.0,
        horse_weight="480(+4)",
        pace="M",
        position_at_corners="3-3-2-1",
        race_class="3勝クラス",
    )
    defaults.update(overrides)
    return PastRaceRecord(**defaults)


def _make_horse_history(horse_id: str = "horse_0001", num_recent: int = 3) -> HorseHistory:
    """テスト用 HorseHistory を生成する。"""
    recent = [_make_past_record(result_order=i + 1) for i in range(num_recent)]
    return HorseHistory(
        horse_id=horse_id,
        horse_name="テスト馬",
        total_runs=20,
        wins=5,
        places=4,
        shows=3,
        recent_results=recent,
        surface_stats={
            "芝": {"runs": 15, "wins": 4, "places": 3, "shows": 2},
            "ダート": {"runs": 5, "wins": 1, "places": 1, "shows": 1},
        },
        distance_stats={
            "1800-2200": {"runs": 10, "wins": 3, "places": 2, "shows": 1},
        },
        venue_stats={
            "中山": {"runs": 8, "wins": 2, "places": 2, "shows": 1},
        },
        running_style="差し",
    )


def _make_jockey_stats(jockey_id: str = "jockey_0001") -> JockeyStats:
    """テスト用 JockeyStats を生成する。"""
    return JockeyStats(
        jockey_id=jockey_id,
        jockey_name="テスト騎手",
        year_runs=150,
        year_wins=25,
        year_win_rate=0.167,
        year_place_rate=0.30,
        year_show_rate=0.40,
        venue_stats={
            "中山": {"runs": 30, "win_rate": 0.15, "show_rate": 0.35},
        },
    )


def _make_trainer_stats(trainer_id: str = "trainer_0001") -> TrainerStats:
    """テスト用 TrainerStats を生成する。"""
    return TrainerStats(
        trainer_id=trainer_id,
        trainer_name="テスト調教師",
        year_runs=80,
        year_wins=12,
        year_win_rate=0.15,
        year_show_rate=0.30,
    )


def _make_odds_data(race_id: str = "202501010101") -> OddsData:
    """テスト用 OddsData を生成する。"""
    return OddsData(
        race_id=race_id,
        win_odds={1: 3.5, 2: 8.0, 3: 15.0},
        place_odds={1: (1.2, 1.8), 2: (2.0, 3.5), 3: (3.0, 5.0)},
        quinella_odds={"1-2": 12.0, "1-3": 25.0, "2-3": 45.0},
        exacta_odds={"1>2": 20.0, "2>1": 30.0},
        bracket_quinella_odds={"1-1": 8.0},
        wide_odds={"1-2": (3.0, 5.0), "1-3": (5.0, 10.0)},
        trio_odds={"1-2-3": 80.0},
        trifecta_odds={"1>2>3": 250.0},
        timestamp="2025-01-01T10:00:00",
    )


def _make_race_with_entries(
    num_entries: int = 3,
    include_histories: bool = True,
    include_odds: bool = True,
) -> UpcomingRaceWithEntries:
    """テスト用 UpcomingRaceWithEntries を生成する。"""
    race_id = "202501010101"
    entries = [_make_entry(horse_number=i + 1) for i in range(num_entries)]

    horse_histories = {}
    jockey_stats = {}
    trainer_stats = {}
    if include_histories:
        for e in entries:
            horse_histories[e.horse_id] = _make_horse_history(e.horse_id)
            jockey_stats[e.jockey_id] = _make_jockey_stats(e.jockey_id)
            trainer_stats[e.trainer_id] = _make_trainer_stats(e.trainer_id)

    odds = _make_odds_data(race_id) if include_odds else None

    return UpcomingRaceWithEntries(
        race_id=race_id,
        race_name="テスト重賞",
        race_date="2025-01-01",
        venue="中山",
        surface="芝",
        distance=2000,
        race_class="G3",
        age_condition="3歳以上",
        number_of_entries=num_entries,
        entries=entries,
        horse_histories=horse_histories,
        jockey_stats=jockey_stats,
        trainer_stats=trainer_stats,
        odds=odds,
    )


# ===========================================================================
# UpcomingHorseEntry のテスト
# ===========================================================================


class TestUpcomingHorseEntry:
    """UpcomingHorseEntry の to_dict / from_dict テスト。"""

    def test_round_trip(self):
        """to_dict → from_dict でデータが一致すること。"""
        entry = _make_entry(horse_number=5, morning_odds=3.5, popularity=2)
        d = entry.to_dict()
        restored = UpcomingHorseEntry.from_dict(d)
        assert restored.entry_id == entry.entry_id
        assert restored.horse_number == entry.horse_number
        assert restored.horse_name == entry.horse_name
        assert restored.weight_carry == entry.weight_carry
        assert restored.morning_odds == entry.morning_odds
        assert restored.popularity == entry.popularity

    def test_none_optional_fields(self):
        """Optional フィールドが None のままラウンドトリップできること。"""
        entry = _make_entry(morning_odds=None, popularity=None, horse_weight=None)
        d = entry.to_dict()
        restored = UpcomingHorseEntry.from_dict(d)
        assert restored.morning_odds is None
        assert restored.popularity is None
        assert restored.horse_weight is None

    def test_dict_keys_are_complete(self):
        """to_dict() の出力にすべてのキーが含まれること。"""
        entry = _make_entry()
        d = entry.to_dict()
        expected_keys = {
            "entry_id", "race_id", "frame_number", "horse_number",
            "horse_name", "horse_id", "sex_age", "weight_carry",
            "jockey_name", "jockey_id", "trainer_name", "trainer_id",
            "horse_weight", "morning_odds", "popularity",
        }
        assert set(d.keys()) == expected_keys


# ===========================================================================
# PastRaceRecord のテスト
# ===========================================================================


class TestPastRaceRecord:
    """PastRaceRecord の to_dict / from_dict テスト。"""

    def test_round_trip(self):
        """全フィールドがラウンドトリップで保存されること。"""
        rec = _make_past_record()
        d = rec.to_dict()
        restored = PastRaceRecord.from_dict(d)
        assert restored.race_date == rec.race_date
        assert restored.venue == rec.venue
        assert restored.distance == rec.distance
        assert restored.result_order == rec.result_order
        assert restored.last_3f == rec.last_3f
        assert restored.time_str == rec.time_str
        assert restored.race_class == rec.race_class

    def test_none_optional_fields(self):
        """取消等で result_order が None の場合。"""
        rec = _make_past_record(result_order=None, time_str=None, last_3f=None)
        d = rec.to_dict()
        restored = PastRaceRecord.from_dict(d)
        assert restored.result_order is None
        assert restored.time_str is None
        assert restored.last_3f is None

    def test_default_race_class(self):
        """race_class が空文字列でデフォルト設定される場合。"""
        d = _make_past_record().to_dict()
        del d["race_class"]
        restored = PastRaceRecord.from_dict(d)
        assert restored.race_class == ""


# ===========================================================================
# HorseHistory のテスト
# ===========================================================================


class TestHorseHistory:
    """HorseHistory の to_dict / from_dict テスト。"""

    def test_round_trip_with_recent_results(self):
        """recent_results を含むラウンドトリップ。"""
        history = _make_horse_history(num_recent=5)
        d = history.to_dict()
        restored = HorseHistory.from_dict(d)
        assert restored.horse_id == history.horse_id
        assert restored.total_runs == history.total_runs
        assert restored.wins == history.wins
        assert len(restored.recent_results) == 5
        assert restored.running_style == "差し"

    def test_empty_recent_results(self):
        """recent_results が空リストの場合。"""
        history = _make_horse_history(num_recent=0)
        d = history.to_dict()
        restored = HorseHistory.from_dict(d)
        assert restored.recent_results == []

    def test_surface_stats_preserved(self):
        """surface_stats のデータが保存されること。"""
        history = _make_horse_history()
        d = history.to_dict()
        restored = HorseHistory.from_dict(d)
        assert "芝" in restored.surface_stats
        assert restored.surface_stats["芝"]["wins"] == 4

    def test_empty_stats_dicts(self):
        """統計辞書が空の場合のフォールバック。"""
        d = {
            "horse_id": "h001",
            "horse_name": "テスト",
            "total_runs": 0,
            "wins": 0,
            "places": 0,
            "shows": 0,
        }
        restored = HorseHistory.from_dict(d)
        assert restored.surface_stats == {}
        assert restored.distance_stats == {}
        assert restored.venue_stats == {}
        assert restored.recent_results == []
        assert restored.running_style == ""


# ===========================================================================
# JockeyStats のテスト
# ===========================================================================


class TestJockeyStats:
    """JockeyStats の to_dict / from_dict テスト。"""

    def test_round_trip(self):
        """全フィールドのラウンドトリップ。"""
        js = _make_jockey_stats()
        d = js.to_dict()
        restored = JockeyStats.from_dict(d)
        assert restored.jockey_id == js.jockey_id
        assert restored.year_win_rate == pytest.approx(js.year_win_rate)
        assert restored.year_show_rate == pytest.approx(js.year_show_rate)
        assert "中山" in restored.venue_stats

    def test_defaults_for_missing_fields(self):
        """最小限のフィールドだけでも from_dict できること。"""
        d = {"jockey_id": "j001", "jockey_name": "テスト"}
        restored = JockeyStats.from_dict(d)
        assert restored.year_runs == 0
        assert restored.year_win_rate == 0.0
        assert restored.venue_stats == {}


# ===========================================================================
# TrainerStats のテスト
# ===========================================================================


class TestTrainerStats:
    """TrainerStats の to_dict / from_dict テスト。"""

    def test_round_trip(self):
        """全フィールドのラウンドトリップ。"""
        ts = _make_trainer_stats()
        d = ts.to_dict()
        restored = TrainerStats.from_dict(d)
        assert restored.trainer_id == ts.trainer_id
        assert restored.year_runs == ts.year_runs
        assert restored.year_win_rate == pytest.approx(ts.year_win_rate)

    def test_defaults_for_missing_fields(self):
        """最小限のフィールドだけでも from_dict できること。"""
        d = {"trainer_id": "t001", "trainer_name": "テスト"}
        restored = TrainerStats.from_dict(d)
        assert restored.year_runs == 0
        assert restored.year_win_rate == 0.0


# ===========================================================================
# OddsData のテスト
# ===========================================================================


class TestOddsData:
    """OddsData の to_dict / from_dict テスト。"""

    def test_round_trip(self):
        """全券種オッズがラウンドトリップで保存されること。"""
        odds = _make_odds_data()
        d = odds.to_dict()
        restored = OddsData.from_dict(d)
        # 単勝オッズ（キーは int に変換される）
        assert restored.win_odds[1] == 3.5
        assert restored.win_odds[3] == 15.0
        # 複勝オッズ（タプル）
        assert restored.place_odds[1] == (1.2, 1.8)
        # 馬連
        assert restored.quinella_odds["1-2"] == 12.0
        # ワイド（タプル）
        assert restored.wide_odds["1-2"] == (3.0, 5.0)
        # 三連複・三連単
        assert restored.trio_odds["1-2-3"] == 80.0
        assert restored.trifecta_odds["1>2>3"] == 250.0

    def test_empty_odds(self):
        """全券種が空の場合。"""
        odds = OddsData(race_id="test_empty")
        d = odds.to_dict()
        restored = OddsData.from_dict(d)
        assert restored.win_odds == {}
        assert restored.place_odds == {}
        assert restored.quinella_odds == {}
        assert restored.wide_odds == {}
        assert restored.timestamp == ""

    def test_win_odds_key_type_after_round_trip(self):
        """to_dict で str になったキーが from_dict で int に戻ること。"""
        odds = _make_odds_data()
        d = odds.to_dict()
        # to_dict では str キー
        assert "1" in d["win_odds"]
        # from_dict で int に戻る
        restored = OddsData.from_dict(d)
        assert 1 in restored.win_odds


# ===========================================================================
# UpcomingRaceWithEntries のテスト
# ===========================================================================


class TestUpcomingRaceWithEntries:
    """UpcomingRaceWithEntries の to_dict / from_dict テスト。"""

    def test_full_round_trip(self):
        """全データを含むラウンドトリップ。"""
        race = _make_race_with_entries(num_entries=3)
        d = race.to_dict()
        restored = UpcomingRaceWithEntries.from_dict(d)
        assert restored.race_id == race.race_id
        assert restored.race_name == race.race_name
        assert restored.distance == race.distance
        assert len(restored.entries) == 3
        assert len(restored.horse_histories) == 3
        assert len(restored.jockey_stats) == 3
        assert len(restored.trainer_stats) == 3
        assert restored.odds is not None
        assert restored.odds.race_id == race.odds.race_id

    def test_without_odds(self):
        """odds が None のラウンドトリップ。"""
        race = _make_race_with_entries(include_odds=False)
        d = race.to_dict()
        restored = UpcomingRaceWithEntries.from_dict(d)
        assert restored.odds is None

    def test_empty_entries(self):
        """出走馬0頭のラウンドトリップ。"""
        race = _make_race_with_entries(num_entries=0, include_histories=False)
        d = race.to_dict()
        restored = UpcomingRaceWithEntries.from_dict(d)
        assert restored.entries == []
        assert restored.horse_histories == {}

    def test_nested_data_integrity(self):
        """ネストしたデータ（馬歴の過去成績）が正しく復元されること。"""
        race = _make_race_with_entries(num_entries=1)
        d = race.to_dict()
        restored = UpcomingRaceWithEntries.from_dict(d)
        horse_id = restored.entries[0].horse_id
        history = restored.horse_histories[horse_id]
        assert len(history.recent_results) == 3
        assert history.recent_results[0].venue == "中山"
