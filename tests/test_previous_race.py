"""
前走データ計算バッチのテスト。
"""
import pytest
from datetime import date
from pathlib import Path

from src.data.schema import Race, HorseEntry
from src.data import storage
from src.data.previous_race import compute_previous_race_data


@pytest.fixture
def setup_races(tmp_path):
    """2レース分のテストデータを作成"""
    # レース1: 1月6日
    race1 = Race(
        race_id="R001",
        date=date(2024, 1, 6),
        venue="中山",
        distance=1200,
        surface="芝",
        race_class="未勝利",
        age_condition="3歳",
    )
    entries1 = [
        HorseEntry(
            entry_id="R001_01", race_id="R001",
            frame_number=1, horse_number=1, horse_name="馬A",
            result_order=1, final_odds=3.0, weight=57.0,
        ),
        HorseEntry(
            entry_id="R001_02", race_id="R001",
            frame_number=2, horse_number=2, horse_name="馬B",
            result_order=3, final_odds=5.0, weight=55.0,
        ),
    ]

    # レース2: 1月13日（馬Aと馬Bが再出走）
    race2 = Race(
        race_id="R002",
        date=date(2024, 1, 13),
        venue="中山",
        distance=1600,
        surface="芝",
        race_class="1勝",
        age_condition="3歳",
    )
    entries2 = [
        HorseEntry(
            entry_id="R002_01", race_id="R002",
            frame_number=1, horse_number=1, horse_name="馬A",
            result_order=2, final_odds=4.0, weight=57.0,
        ),
        HorseEntry(
            entry_id="R002_02", race_id="R002",
            frame_number=2, horse_number=2, horse_name="馬B",
            result_order=1, final_odds=2.0, weight=55.0,
        ),
        HorseEntry(
            entry_id="R002_03", race_id="R002",
            frame_number=3, horse_number=3, horse_name="馬C",
            result_order=3, final_odds=10.0, weight=54.0,
        ),
    ]

    storage.save_races([race1, race2], tmp_path)
    storage.save_entries("R001", entries1, tmp_path)
    storage.save_entries("R002", entries2, tmp_path)

    return tmp_path


class TestComputePreviousRaceData:
    def test_previous_order_set(self, setup_races):
        """前走着順が正しく設定される"""
        compute_previous_race_data(base_path=setup_races)

        # レース2の馬Aの前走着順 = レース1の着順(1)
        entries = storage.load_entries("R002", setup_races)
        horse_a = [e for e in entries if e.horse_name == "馬A"][0]
        assert horse_a.previous_order == 1

    def test_previous_distance_set(self, setup_races):
        """前走距離が正しく設定される"""
        compute_previous_race_data(base_path=setup_races)

        # レース2の馬Aの前走距離 = レース1の距離(1200)
        entries = storage.load_entries("R002", setup_races)
        horse_a = [e for e in entries if e.horse_name == "馬A"][0]
        assert horse_a.previous_distance == 1200

    def test_first_race_no_previous(self, setup_races):
        """初出走の馬は前走データなし"""
        compute_previous_race_data(base_path=setup_races)

        # レース1の馬Aは前走なし
        entries = storage.load_entries("R001", setup_races)
        horse_a = [e for e in entries if e.horse_name == "馬A"][0]
        assert horse_a.previous_order is None
        assert horse_a.previous_distance is None

    def test_new_horse_no_previous(self, setup_races):
        """途中参戦の馬は前走データなし"""
        compute_previous_race_data(base_path=setup_races)

        # レース2の馬Cは初出走
        entries = storage.load_entries("R002", setup_races)
        horse_c = [e for e in entries if e.horse_name == "馬C"][0]
        assert horse_c.previous_order is None

    def test_return_value(self, setup_races):
        """更新したレース数を返す"""
        updated = compute_previous_race_data(base_path=setup_races)
        # レース2が更新される（馬A, 馬Bの前走データ）
        assert updated >= 1

    def test_empty(self, tmp_path):
        """レースがない場合は0"""
        assert compute_previous_race_data(base_path=tmp_path) == 0

    def test_idempotent(self, setup_races):
        """2回実行しても結果は同じ"""
        compute_previous_race_data(base_path=setup_races)
        entries_first = storage.load_entries("R002", setup_races)

        compute_previous_race_data(base_path=setup_races)
        entries_second = storage.load_entries("R002", setup_races)

        for e1, e2 in zip(entries_first, entries_second):
            assert e1.previous_order == e2.previous_order
            assert e1.previous_distance == e2.previous_distance

    def test_preserves_other_fields(self, setup_races):
        """前走データ更新時に他のフィールドが保持される"""
        compute_previous_race_data(base_path=setup_races)

        entries = storage.load_entries("R002", setup_races)
        horse_a = [e for e in entries if e.horse_name == "馬A"][0]
        assert horse_a.final_odds == 4.0
        assert horse_a.weight == 57.0
        assert horse_a.result_order == 2
