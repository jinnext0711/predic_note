"""導出指標（data/derived_indicators.py）のテスト。"""
import pytest
from data.schema import HorseEntry
from data.derived_indicators import (
    count_nige, count_senko, calc_avg_position_4c,
    calc_diff_from_avg, classify_pace,
    compute_race_indicators, compute_horse_indicators, compute_all,
)


def _make_entry(entry_id: str, pos_4c=None, **kwargs) -> HorseEntry:
    """テスト用 HorseEntry を生成するヘルパー。"""
    return HorseEntry(
        entry_id=entry_id,
        race_id="R001",
        frame_number=1,
        horse_number=1,
        horse_name=f"馬{entry_id}",
        previous_position_4c=pos_4c,
        **kwargs,
    )


class TestCountNige:
    def test_nige_positions_1_and_2(self):
        entries = [_make_entry("1", pos_4c=1), _make_entry("2", pos_4c=2), _make_entry("3", pos_4c=3)]
        assert count_nige(entries) == 2

    def test_no_nige(self):
        entries = [_make_entry("1", pos_4c=5), _make_entry("2", pos_4c=6)]
        assert count_nige(entries) == 0

    def test_none_position_ignored(self):
        entries = [_make_entry("1", pos_4c=None), _make_entry("2", pos_4c=1)]
        assert count_nige(entries) == 1


class TestCountSenko:
    def test_senko_positions_3_and_4(self):
        entries = [_make_entry("1", pos_4c=3), _make_entry("2", pos_4c=4), _make_entry("3", pos_4c=5)]
        assert count_senko(entries) == 2

    def test_no_senko(self):
        entries = [_make_entry("1", pos_4c=1), _make_entry("2", pos_4c=8)]
        assert count_senko(entries) == 0


class TestCalcAvgPosition4c:
    def test_basic_average(self):
        entries = [_make_entry("1", pos_4c=2), _make_entry("2", pos_4c=4)]
        assert calc_avg_position_4c(entries) == 3.0

    def test_none_ignored(self):
        entries = [_make_entry("1", pos_4c=2), _make_entry("2", pos_4c=None)]
        assert calc_avg_position_4c(entries) == 2.0

    def test_all_none(self):
        entries = [_make_entry("1", pos_4c=None)]
        assert calc_avg_position_4c(entries) is None

    def test_empty_entries(self):
        assert calc_avg_position_4c([]) is None


class TestCalcDiffFromAvg:
    def test_positive_diff(self):
        entry = _make_entry("1", pos_4c=6)
        assert calc_diff_from_avg(entry, 4.0) == 2.0

    def test_negative_diff(self):
        entry = _make_entry("1", pos_4c=2)
        assert calc_diff_from_avg(entry, 4.0) == -2.0

    def test_none_entry(self):
        entry = _make_entry("1", pos_4c=None)
        assert calc_diff_from_avg(entry, 4.0) is None

    def test_none_avg(self):
        entry = _make_entry("1", pos_4c=3)
        assert calc_diff_from_avg(entry, None) is None


class TestClassifyPace:
    def test_fast_pace(self):
        # 5頭中3頭が4角位置4以内 → 60% > 40% → 速
        entries = [
            _make_entry("1", pos_4c=1), _make_entry("2", pos_4c=2),
            _make_entry("3", pos_4c=3), _make_entry("4", pos_4c=8),
            _make_entry("5", pos_4c=10),
        ]
        assert classify_pace(entries) == "速"

    def test_slow_pace(self):
        # 10頭中1頭だけ4角位置4以内 → 10% < 20% → 遅
        entries = [_make_entry(str(i), pos_4c=i) for i in range(1, 11)]
        # pos_4c 1,2,3,4 → 4頭/10 = 40% → ちょうど40%は普
        # もっと後方を増やす
        entries = [_make_entry("1", pos_4c=3)] + [_make_entry(str(i), pos_4c=i+5) for i in range(2, 11)]
        assert classify_pace(entries) == "遅"

    def test_normal_pace(self):
        # 5頭中1頭が4角位置4以内 → 20% → 普（20%未満ではない、40%超でもない）
        entries = [
            _make_entry("1", pos_4c=2),
            _make_entry("2", pos_4c=5), _make_entry("3", pos_4c=6),
            _make_entry("4", pos_4c=7), _make_entry("5", pos_4c=8),
        ]
        assert classify_pace(entries) == "普"

    def test_no_data(self):
        entries = [_make_entry("1", pos_4c=None)]
        assert classify_pace(entries) == "普"

    def test_empty(self):
        assert classify_pace([]) == "普"


class TestComputeAll:
    def test_compute_all_returns_tuple(self):
        entries = [_make_entry("1", pos_4c=1), _make_entry("2", pos_4c=5)]
        race_ind, horse_inds = compute_all("R001", entries)
        assert race_ind.race_id == "R001"
        assert race_ind.nige_count == 1
        assert race_ind.senko_count == 0
        assert len(horse_inds) == 2
