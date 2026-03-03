"""
未来レースデータの保存・読み込み (upcoming_storage.py) のテスト。

tmp_path フィクスチャを使用して、各関数のラウンドトリップ、
存在しないファイルの読み込み、一覧取得を検証する。
"""
import json
import pytest
from pathlib import Path

from data.shutuba_schema import (
    OddsData,
    UpcomingHorseEntry,
    UpcomingRaceWithEntries,
)
from data.upcoming_storage import (
    load_analysis,
    load_article,
    load_strategy,
    load_upcoming_race,
    list_upcoming_race_ids,
    save_analysis,
    save_article,
    save_strategy,
    save_upcoming_race,
)


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _make_entry(horse_number: int = 1, race_id: str = "202501010101") -> UpcomingHorseEntry:
    """テスト用の出馬表エントリを生成する。"""
    return UpcomingHorseEntry(
        entry_id=f"{race_id}_{horse_number:02d}",
        race_id=race_id,
        frame_number=1,
        horse_number=horse_number,
        horse_name=f"テスト馬{horse_number}",
        horse_id=f"horse_{horse_number:04d}",
        sex_age="牡3",
        weight_carry=57.0,
        jockey_name="テスト騎手",
        jockey_id="jockey_0001",
        trainer_name="テスト調教師",
        trainer_id="trainer_0001",
    )


def _make_race(race_id: str = "202501010101", num_entries: int = 2) -> UpcomingRaceWithEntries:
    """テスト用 UpcomingRaceWithEntries を生成する。"""
    return UpcomingRaceWithEntries(
        race_id=race_id,
        race_name="テストレース",
        race_date="2025-01-01",
        venue="中山",
        surface="芝",
        distance=2000,
        race_class="G3",
        age_condition="3歳以上",
        number_of_entries=num_entries,
        entries=[_make_entry(i + 1, race_id) for i in range(num_entries)],
    )


# ===========================================================================
# save_upcoming_race / load_upcoming_race のテスト
# ===========================================================================


class TestSaveLoadUpcomingRace:
    """出馬表データの保存・読み込みテスト。"""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """保存したデータを読み込んで一致すること。"""
        race = _make_race()
        save_upcoming_race(race, base_path=tmp_path)
        loaded = load_upcoming_race(race.race_id, base_path=tmp_path)

        assert loaded is not None
        assert loaded.race_id == race.race_id
        assert loaded.race_name == race.race_name
        assert loaded.venue == race.venue
        assert loaded.distance == race.distance
        assert len(loaded.entries) == 2
        assert loaded.entries[0].horse_name == "テスト馬1"

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """存在しない race_id の読み込みは None を返すこと。"""
        result = load_upcoming_race("nonexistent_race", base_path=tmp_path)
        assert result is None

    def test_save_creates_correct_directory_structure(self, tmp_path: Path):
        """保存先のディレクトリ構造が正しく作られること。"""
        race = _make_race(race_id="202501010102")
        path = save_upcoming_race(race, base_path=tmp_path)
        assert path.exists()
        assert path.name == "shutuba.json"
        assert path.parent.name == "202501010102"

    def test_overwrite_existing(self, tmp_path: Path):
        """同じ race_id で上書き保存できること。"""
        race1 = _make_race(race_id="202501010101", num_entries=2)
        save_upcoming_race(race1, base_path=tmp_path)

        race2 = _make_race(race_id="202501010101", num_entries=5)
        save_upcoming_race(race2, base_path=tmp_path)

        loaded = load_upcoming_race("202501010101", base_path=tmp_path)
        assert loaded is not None
        assert len(loaded.entries) == 5

    def test_json_is_valid_utf8(self, tmp_path: Path):
        """保存された JSON が UTF-8 で正しく読み取れること。"""
        race = _make_race()
        path = save_upcoming_race(race, base_path=tmp_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["race_name"] == "テストレース"
        assert data["venue"] == "中山"


# ===========================================================================
# save_analysis / load_analysis のテスト
# ===========================================================================


class TestSaveLoadAnalysis:
    """分析結果の保存・読み込みテスト。"""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """分析結果がラウンドトリップで保存されること。"""
        race_id = "202501010101"
        analysis = {
            "race_id": race_id,
            "evaluations": [
                {"horse_number": 1, "total_index": 85.5, "mark": "◎"},
                {"horse_number": 2, "total_index": 72.0, "mark": "○"},
            ],
            "volatility": "上位拮抗",
        }
        save_analysis(race_id, analysis, base_path=tmp_path)
        loaded = load_analysis(race_id, base_path=tmp_path)

        assert loaded is not None
        assert loaded["race_id"] == race_id
        assert len(loaded["evaluations"]) == 2
        assert loaded["volatility"] == "上位拮抗"

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """存在しない分析結果は None を返すこと。"""
        result = load_analysis("nonexistent", base_path=tmp_path)
        assert result is None


# ===========================================================================
# save_strategy / load_strategy のテスト
# ===========================================================================


class TestSaveLoadStrategy:
    """買い目戦略の保存・読み込みテスト。"""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """戦略データがラウンドトリップで保存されること。"""
        race_id = "202501010101"
        strategy = {
            "race_id": race_id,
            "best_bet_type": "ワイド",
            "total_investment": 5000,
            "aggressive_bets": [
                {"bet_type": "三連単", "selection": "1>2>3", "amount": 300},
            ],
        }
        save_strategy(race_id, strategy, base_path=tmp_path)
        loaded = load_strategy(race_id, base_path=tmp_path)

        assert loaded is not None
        assert loaded["best_bet_type"] == "ワイド"
        assert loaded["total_investment"] == 5000
        assert len(loaded["aggressive_bets"]) == 1

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """存在しない戦略は None を返すこと。"""
        result = load_strategy("nonexistent", base_path=tmp_path)
        assert result is None


# ===========================================================================
# save_article / load_article のテスト
# ===========================================================================


class TestSaveLoadArticle:
    """記事テキストの保存・読み込みテスト。"""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """記事テキストがラウンドトリップで保存されること。"""
        text = "# テスト記事\n\n本日の予想です。"
        race_date = "2025-01-01"
        save_article(text, race_date, base_path=tmp_path)
        loaded = load_article(race_date, base_path=tmp_path)

        assert loaded is not None
        assert loaded == text

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        """存在しない記事は None を返すこと。"""
        result = load_article("2099-12-31", base_path=tmp_path)
        assert result is None

    def test_japanese_content_preserved(self, tmp_path: Path):
        """日本語コンテンツが正しく保存・読み込みされること。"""
        text = "◎テスト馬1　○テスト馬2　▲テスト馬3\n三連単 1>2>3"
        save_article(text, "2025-03-01", base_path=tmp_path)
        loaded = load_article("2025-03-01", base_path=tmp_path)
        assert loaded == text

    def test_save_creates_article_file(self, tmp_path: Path):
        """記事ファイルが articles/ ディレクトリに作られること。"""
        path = save_article("テスト", "2025-01-01", base_path=tmp_path)
        assert path.exists()
        assert "articles" in str(path.parent)
        assert path.name == "2025-01-01_article.md"


# ===========================================================================
# list_upcoming_race_ids のテスト
# ===========================================================================


class TestListUpcomingRaceIds:
    """保存済みレース一覧取得のテスト。"""

    def test_empty_directory(self, tmp_path: Path):
        """データなしの場合は空リストを返すこと。"""
        ids = list_upcoming_race_ids(base_path=tmp_path)
        assert ids == []

    def test_lists_saved_races(self, tmp_path: Path):
        """保存したレースの ID が一覧に含まれること。"""
        race1 = _make_race(race_id="race_A")
        race2 = _make_race(race_id="race_B")
        save_upcoming_race(race1, base_path=tmp_path)
        save_upcoming_race(race2, base_path=tmp_path)

        ids = list_upcoming_race_ids(base_path=tmp_path)
        assert "race_A" in ids
        assert "race_B" in ids
        assert len(ids) == 2

    def test_ignores_directories_without_shutuba_json(self, tmp_path: Path):
        """shutuba.json がないディレクトリは無視されること。"""
        # 正しいレースを1つ保存
        race = _make_race(race_id="valid_race")
        save_upcoming_race(race, base_path=tmp_path)

        # shutuba.json がないダミーディレクトリを作成
        dummy_dir = tmp_path / "data" / "upcoming" / "dummy_dir"
        dummy_dir.mkdir(parents=True, exist_ok=True)

        ids = list_upcoming_race_ids(base_path=tmp_path)
        assert "valid_race" in ids
        assert "dummy_dir" not in ids

    def test_sorted_order(self, tmp_path: Path):
        """一覧がソートされて返されること。"""
        for rid in ["race_C", "race_A", "race_B"]:
            save_upcoming_race(_make_race(race_id=rid), base_path=tmp_path)

        ids = list_upcoming_race_ids(base_path=tmp_path)
        assert ids == sorted(ids)
