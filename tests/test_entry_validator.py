"""entry_validator モジュールのテスト。"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data.entry_validator import (
    EntryIssue,
    EntryStatus,
    EntryValidationResult,
    MAX_MISSING_JOCKEYS_RATIO,
    MIN_ENTRIES_FOR_RACE,
    PARTIAL_MISSING_JOCKEYS_RATIO,
    validate_all_races,
    validate_entries,
)
from data.shutuba_schema import UpcomingHorseEntry, UpcomingRaceWithEntries


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _make_entry(
    horse_number: int = 1,
    horse_name: str = "テスト馬",
    horse_id: str = "horse_001",
    jockey_name: str = "テスト騎手",
    jockey_id: str = "jockey_001",
    weight_carry: float = 57.0,
    trainer_name: str = "テスト調教師",
    trainer_id: str = "trainer_001",
) -> UpcomingHorseEntry:
    """テスト用の出馬表エントリーを作成する。"""
    return UpcomingHorseEntry(
        entry_id=f"race_001_{horse_number:02d}",
        race_id="race_001",
        frame_number=horse_number,
        horse_number=horse_number,
        horse_name=f"{horse_name}{horse_number}",
        horse_id=f"{horse_id}_{horse_number:03d}" if horse_id else "",
        sex_age="牡3",
        weight_carry=weight_carry,
        jockey_name=jockey_name if jockey_name else "",
        jockey_id=jockey_id if jockey_id else "",
        trainer_name=trainer_name,
        trainer_id=trainer_id,
    )


def _make_race(
    num_entries: int = 10,
    race_id: str = "202506010101",
    race_name: str = "テストレース",
    **entry_overrides,
) -> UpcomingRaceWithEntries:
    """テスト用のレースデータを作成する。"""
    entries = [
        _make_entry(horse_number=i + 1, **entry_overrides)
        for i in range(num_entries)
    ]
    return UpcomingRaceWithEntries(
        race_id=race_id,
        race_name=race_name,
        race_date="2026-03-07",
        venue="中山",
        surface="芝",
        distance=2000,
        race_class="3歳未勝利",
        age_condition="3歳",
        number_of_entries=num_entries,
        entries=entries,
    )


# ---------------------------------------------------------------------------
# テストクラス
# ---------------------------------------------------------------------------


class TestValidateEntries:
    """validate_entries のテスト。"""

    def test_confirmed_race(self):
        """全項目正常なレース → CONFIRMED"""
        race = _make_race(num_entries=10)
        result = validate_entries(race)
        assert result.status == EntryStatus.CONFIRMED
        assert result.is_analyzable is True
        assert len(result.issues) == 0
        assert "確定済み" in result.summary

    def test_not_available_no_entries(self):
        """エントリー0頭 → NOT_AVAILABLE"""
        race = _make_race(num_entries=0)
        race.entries = []
        result = validate_entries(race)
        assert result.status == EntryStatus.NOT_AVAILABLE
        assert result.is_analyzable is False
        assert "取得できません" in result.summary

    def test_unconfirmed_too_few_entries(self):
        """エントリー数不足 → UNCONFIRMED"""
        race = _make_race(num_entries=4)
        result = validate_entries(race)
        assert result.status == EntryStatus.UNCONFIRMED
        assert result.is_analyzable is False
        assert "出走頭数が不足" in result.summary

    def test_unconfirmed_exactly_at_min(self):
        """ちょうど最低頭数 → CONFIRMED（境界テスト）"""
        race = _make_race(num_entries=MIN_ENTRIES_FOR_RACE)
        result = validate_entries(race)
        assert result.status == EntryStatus.CONFIRMED

    def test_unconfirmed_many_jockeys_missing(self):
        """騎手未定が30%以上 → UNCONFIRMED"""
        race = _make_race(num_entries=10)
        # 10頭中4頭の騎手を未定に（40% > 30%）
        for i in range(4):
            race.entries[i].jockey_name = ""
            race.entries[i].jockey_id = ""
        result = validate_entries(race)
        assert result.status == EntryStatus.UNCONFIRMED
        assert result.is_analyzable is False
        assert "騎手未定が多数" in result.summary

    def test_unconfirmed_exactly_at_threshold(self):
        """騎手未定がちょうど30% → UNCONFIRMED（境界テスト）"""
        race = _make_race(num_entries=10)
        # 10頭中3頭の騎手を未定に（30% == 閾値）
        for i in range(3):
            race.entries[i].jockey_name = ""
            race.entries[i].jockey_id = ""
        result = validate_entries(race)
        assert result.status == EntryStatus.UNCONFIRMED

    def test_partially_confirmed_one_jockey_missing(self):
        """騎手未定1頭（10%） → PARTIALLY_CONFIRMED"""
        race = _make_race(num_entries=10)
        race.entries[0].jockey_name = ""
        race.entries[0].jockey_id = ""
        result = validate_entries(race)
        assert result.status == EntryStatus.PARTIALLY_CONFIRMED
        assert result.is_analyzable is True
        assert "騎手未定" in result.summary

    def test_partially_confirmed_jockey_below_partial_threshold(self):
        """騎手未定が10%未満 → CONFIRMED"""
        race = _make_race(num_entries=20)
        # 20頭中1頭（5% < 10%）でも jockey_name が空なら issue にはなる
        race.entries[0].jockey_name = ""
        race.entries[0].jockey_id = ""
        result = validate_entries(race)
        # 5% < PARTIAL_MISSING_JOCKEYS_RATIO(10%) だが、
        # issue が1件はあるが ratio が閾値以下なので他のチェック次第
        # horse_id, weight_carry は正常なので...
        # 実際は 1/20 = 5% < 10% で、horse_id/weight はOK → ？
        # _check_jockey_missing で issue が出るが ratio < 10% で
        # horse_id_missing = 0, weight_missing = 0 → CONFIRMED
        # ただし issue は1件ある
        assert result.status == EntryStatus.CONFIRMED

    def test_partially_confirmed_horse_id_missing(self):
        """horse_id 未設定1頭 → PARTIALLY_CONFIRMED"""
        race = _make_race(num_entries=10)
        race.entries[5].horse_id = ""
        result = validate_entries(race)
        assert result.status == EntryStatus.PARTIALLY_CONFIRMED
        assert result.is_analyzable is True
        assert "馬ID未設定" in result.summary

    def test_partially_confirmed_weight_missing(self):
        """斤量未設定1頭 → PARTIALLY_CONFIRMED"""
        race = _make_race(num_entries=10)
        race.entries[3].weight_carry = 0.0
        result = validate_entries(race)
        assert result.status == EntryStatus.PARTIALLY_CONFIRMED
        assert result.is_analyzable is True
        assert "斤量未設定" in result.summary

    def test_all_jockeys_missing(self):
        """全馬の騎手未定 → UNCONFIRMED"""
        race = _make_race(num_entries=10)
        for entry in race.entries:
            entry.jockey_name = ""
            entry.jockey_id = ""
        result = validate_entries(race)
        assert result.status == EntryStatus.UNCONFIRMED
        assert result.is_analyzable is False

    def test_multiple_issues(self):
        """複数の問題が同時に発生"""
        race = _make_race(num_entries=10)
        race.entries[0].horse_id = ""
        race.entries[1].weight_carry = 0.0
        result = validate_entries(race)
        assert result.status == EntryStatus.PARTIALLY_CONFIRMED
        assert len(result.issues) == 2

    def test_jockey_name_empty_but_id_present(self):
        """jockey_name が空で jockey_id がある → 騎手未定"""
        race = _make_race(num_entries=10)
        race.entries[0].jockey_name = ""
        # jockey_id はあるが name が空
        result = validate_entries(race)
        assert any(i.issue_type == "jockey_missing" for i in result.issues)


class TestIsAnalyzable:
    """is_analyzable プロパティのテスト。"""

    def test_confirmed_is_analyzable(self):
        result = EntryValidationResult(
            race_id="test",
            race_name="テスト",
            status=EntryStatus.CONFIRMED,
        )
        assert result.is_analyzable is True

    def test_partial_is_analyzable(self):
        result = EntryValidationResult(
            race_id="test",
            race_name="テスト",
            status=EntryStatus.PARTIALLY_CONFIRMED,
        )
        assert result.is_analyzable is True

    def test_unconfirmed_not_analyzable(self):
        result = EntryValidationResult(
            race_id="test",
            race_name="テスト",
            status=EntryStatus.UNCONFIRMED,
        )
        assert result.is_analyzable is False

    def test_not_available_not_analyzable(self):
        result = EntryValidationResult(
            race_id="test",
            race_name="テスト",
            status=EntryStatus.NOT_AVAILABLE,
        )
        assert result.is_analyzable is False


class TestValidateAllRaces:
    """validate_all_races のテスト。"""

    def test_multiple_races(self):
        """複数レースの一括検証"""
        race1 = _make_race(num_entries=10, race_id="race_001")
        race2 = _make_race(num_entries=3, race_id="race_002")  # 頭数不足
        race3 = _make_race(num_entries=8, race_id="race_003")

        results = validate_all_races([race1, race2, race3])
        assert len(results) == 3
        assert results[0].status == EntryStatus.CONFIRMED
        assert results[1].status == EntryStatus.UNCONFIRMED
        assert results[2].status == EntryStatus.CONFIRMED

    def test_empty_list(self):
        """空リストの検証"""
        results = validate_all_races([])
        assert len(results) == 0


class TestToDict:
    """to_dict のテスト。"""

    def test_validation_result_to_dict(self):
        """EntryValidationResult のシリアライズ"""
        result = EntryValidationResult(
            race_id="202506010101",
            race_name="テストレース",
            status=EntryStatus.PARTIALLY_CONFIRMED,
            issues=[
                EntryIssue(
                    horse_number=3,
                    horse_name="テスト馬3",
                    issue_type="jockey_missing",
                    description="テスト馬3（3番）: 騎手未定",
                )
            ],
            summary="一部未確定: 騎手未定1頭",
        )
        d = result.to_dict()
        assert d["race_id"] == "202506010101"
        assert d["status"] == "partial"
        assert d["is_analyzable"] is True
        assert len(d["issues"]) == 1
        assert d["issues"][0]["issue_type"] == "jockey_missing"

    def test_entry_issue_to_dict(self):
        """EntryIssue のシリアライズ"""
        issue = EntryIssue(
            horse_number=5,
            horse_name="テスト馬",
            issue_type="weight_carry_missing",
            description="テスト馬（5番）: 斤量未設定",
        )
        d = issue.to_dict()
        assert d["horse_number"] == 5
        assert d["issue_type"] == "weight_carry_missing"
