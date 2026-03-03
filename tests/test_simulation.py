"""simulation.py のテスト（check_simulatable, バックテスト内部ロジック）。"""
import json
import pytest
from datetime import date
from pathlib import Path

from simulation import (
    check_simulatable,
    get_logic_type_info,
    _race_matches_scope,
    _entry_passes_must,
    _rank_entries,
    _compare,
    _get_entry_value,
    run_backtest,
)
from models.simulation_spec import BetType
from data.schema import Race, HorseEntry


# ── check_simulatable ──

class TestCheckSimulatable:
    def test_no_custom_vars(self):
        rec = {"name": "test", "scope": {}, "must": {}}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is True
        assert reason == ""

    def test_empty_custom_vars_legacy_format(self):
        """旧形式（custom_variables リスト）が空の場合はシミュレーション可能。"""
        rec = {"name": "test", "custom_variables": []}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is True

    def test_empty_custom_vars_store_format(self):
        """logic_store 形式（custom_vars dict）が空の場合はシミュレーション可能。"""
        rec = {"name": "test", "custom_vars": {"variables": []}}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is True

    def test_with_custom_vars_legacy_format(self):
        """旧形式でカスタム変数がある場合はシミュレーション不可。"""
        rec = {"name": "test", "custom_variables": [{"name": "気分", "var_type": "真偽値"}]}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is False
        assert "カスタム変数" in reason

    def test_with_custom_vars_store_format(self):
        """logic_store 形式でカスタム変数がある場合はシミュレーション不可。"""
        rec = {"name": "test", "custom_vars": {"variables": [{"name": "気分", "var_type": "真偽値"}]}}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is False
        assert "カスタム変数" in reason

    def test_custom_var_without_name_ignored(self):
        rec = {"name": "test", "custom_variables": [{"name": "", "var_type": "真偽値"}]}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is True

    def test_custom_vars_store_format_without_name_ignored(self):
        """logic_store 形式で名前が空のカスタム変数は無視される。"""
        rec = {"name": "test", "custom_vars": {"variables": [{"name": "", "var_type": "真偽値"}]}}
        can_sim, reason = check_simulatable(rec)
        assert can_sim is True


# ── get_logic_type_info ──

class TestGetLogicTypeInfo:
    def test_simulatable_logic(self):
        """シミュレーション可能なロジックの情報を返す。"""
        rec = {"name": "test", "scope": {}}
        info = get_logic_type_info(rec)
        assert info["can_simulate"] is True
        assert info["logic_type"] == "シミュレーション可能"
        assert info["reason"] == ""
        assert "バックテスト" in info["description"]

    def test_incapable_logic_with_custom_vars(self):
        """カスタム変数ありでシミュレーション不可なロジックの情報を返す。"""
        rec = {"name": "test", "custom_vars": {"variables": [{"name": "気分", "var_type": "真偽値"}]}}
        info = get_logic_type_info(rec)
        assert info["can_simulate"] is False
        assert info["logic_type"] == "シミュレーション不可"
        assert "カスタム変数" in info["reason"]
        assert "フォワード成績" in info["description"]


# ── _compare ──

class TestCompare:
    def test_eq(self):
        assert _compare(56.0, "eq", "56.0") is True
        assert _compare(56.0, "eq", "57.0") is False

    def test_le(self):
        assert _compare(56.0, "le", "57") is True
        assert _compare(58.0, "le", "57") is False

    def test_ge(self):
        assert _compare(58.0, "ge", "57") is True
        assert _compare(56.0, "ge", "57") is False

    def test_lt(self):
        assert _compare(56.0, "lt", "57") is True
        assert _compare(57.0, "lt", "57") is False

    def test_gt(self):
        assert _compare(58.0, "gt", "57") is True
        assert _compare(57.0, "gt", "57") is False

    def test_none_returns_false(self):
        assert _compare(None, "eq", "1") is False

    def test_invalid_operator(self):
        assert _compare(1, "unknown", "1") is False

    def test_int_comparison(self):
        assert _compare(3, "le", "5") is True
        assert _compare(3, "ge", "5") is False


# ── _race_matches_scope ──

class TestRaceMatchesScope:
    def _make_race(self, **overrides) -> Race:
        defaults = dict(
            race_id="R001", date=date(2024, 6, 1), venue="東京",
            distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上",
        )
        defaults.update(overrides)
        return Race(**defaults)

    def test_full_match(self):
        race = self._make_race()
        scope = {"venues": ["東京"], "distance_min": 1400, "distance_max": 1800,
                 "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}
        assert _race_matches_scope(race, scope) is True

    def test_venue_mismatch(self):
        race = self._make_race(venue="阪神")
        scope = {"venues": ["東京"]}
        assert _race_matches_scope(race, scope) is False

    def test_distance_in_range(self):
        race = self._make_race(distance=1200)
        scope = {"distance_min": 1000, "distance_max": 1400}
        assert _race_matches_scope(race, scope) is True

    def test_distance_exact_boundary(self):
        race = self._make_race(distance=1600)
        scope = {"distance_min": 1600, "distance_max": 1600}
        assert _race_matches_scope(race, scope) is True

    def test_distance_wide_range(self):
        race = self._make_race(distance=2000)
        scope = {"distance_min": 1800, "distance_max": 2400}
        assert _race_matches_scope(race, scope) is True

    def test_distance_long_range(self):
        race = self._make_race(distance=3000)
        scope = {"distance_min": 2400, "distance_max": 3600}
        assert _race_matches_scope(race, scope) is True

    def test_distance_mismatch(self):
        race = self._make_race(distance=1600)
        scope = {"distance_min": 1000, "distance_max": 1400}
        assert _race_matches_scope(race, scope) is False

    def test_legacy_distance_categories(self):
        """旧距離カテゴリ形式が後方互換で動作すること。"""
        race = self._make_race(distance=1600)
        scope = {"distances": ["マイル"]}
        assert _race_matches_scope(race, scope) is True

    def test_empty_scope_matches_all(self):
        race = self._make_race()
        assert _race_matches_scope(race, {}) is True

    def test_multiple_venues_or(self):
        race = self._make_race(venue="中山")
        scope = {"venues": ["東京", "中山"]}
        assert _race_matches_scope(race, scope) is True


# ── _entry_passes_must ──

class TestEntryPassesMust:
    def _make_entry(self, **overrides) -> HorseEntry:
        defaults = dict(
            entry_id="E1", race_id="R001", frame_number=1,
            horse_number=1, horse_name="テスト馬",
            weight=56.0, previous_order=2,
        )
        defaults.update(overrides)
        return HorseEntry(**defaults)

    def test_no_must(self):
        entry = self._make_entry()
        assert _entry_passes_must(entry, None) is True
        assert _entry_passes_must(entry, {}) is True

    def test_single_block_pass(self):
        entry = self._make_entry(weight=56.0)
        must = {"blocks": [{"conditions": [{"category": "斤量", "operator": "le", "value": "57"}]}]}
        assert _entry_passes_must(entry, must) is True

    def test_single_block_fail(self):
        entry = self._make_entry(weight=58.0)
        must = {"blocks": [{"conditions": [{"category": "斤量", "operator": "le", "value": "57"}]}]}
        assert _entry_passes_must(entry, must) is False

    def test_and_between_blocks(self):
        """ブロック間はAND: 両方のブロックを満たす必要がある。"""
        entry = self._make_entry(weight=56.0, previous_order=5)
        must = {"blocks": [
            {"conditions": [{"category": "斤量", "operator": "le", "value": "57"}]},
            {"conditions": [{"category": "前走着順", "operator": "le", "value": "3"}]},
        ]}
        assert _entry_passes_must(entry, must) is False

    def test_or_within_block(self):
        """同一ブロック内はOR: いずれか1つを満たせばOK。"""
        entry = self._make_entry(weight=58.0, previous_order=2)
        must = {"blocks": [{"conditions": [
            {"category": "斤量", "operator": "le", "value": "56"},
            {"category": "前走着順", "operator": "le", "value": "3"},
        ]}]}
        assert _entry_passes_must(entry, must) is True

    def test_empty_conditions_block_skipped(self):
        entry = self._make_entry()
        must = {"blocks": [{"conditions": []}]}
        assert _entry_passes_must(entry, must) is True


# ── _rank_entries ──

class TestRankEntries:
    def _make_entry(self, entry_id, weight=56.0, horse_number=1) -> HorseEntry:
        return HorseEntry(
            entry_id=entry_id, race_id="R001", frame_number=1,
            horse_number=horse_number, horse_name=f"馬{entry_id}",
            weight=weight,
        )

    def test_no_prefer_avoid(self):
        entries = [self._make_entry("A"), self._make_entry("B")]
        result = _rank_entries(entries, None)
        assert result[0].entry_id == "A"

    def test_prefer_sorts_matching_first(self):
        a = self._make_entry("A", weight=57.0)
        b = self._make_entry("B", weight=55.0)
        pa = {"prefer": [{"order": 1, "criteria": {"category": "斤量", "operator": "le", "value": "56"}}], "avoid": []}
        result = _rank_entries([a, b], pa)
        assert result[0].entry_id == "B"

    def test_avoid_pushes_matching_down(self):
        a = self._make_entry("A", horse_number=8)
        b = self._make_entry("B", horse_number=3)
        pa = {"prefer": [], "avoid": [{"criteria": {"category": "枠番／馬番", "operator": "gt", "value": "6"}}]}
        result = _rank_entries([a, b], pa)
        assert result[0].entry_id == "B"

    def test_lexicographic_prefer(self):
        """レキシコグラフィック: 優先順位1が同じなら優先順位2で比較。"""
        a = self._make_entry("A", weight=55.0, horse_number=5)
        b = self._make_entry("B", weight=55.0, horse_number=2)
        pa = {
            "prefer": [
                {"order": 1, "criteria": {"category": "斤量", "operator": "le", "value": "56"}},
                {"order": 2, "criteria": {"category": "枠番／馬番", "operator": "le", "value": "3"}},
            ],
            "avoid": [],
        }
        result = _rank_entries([a, b], pa)
        # 両方 prefer1 を満たす。prefer2: B(2<=3)→match, A(5<=3)→不一致 → B が上位
        assert result[0].entry_id == "B"


# ── run_backtest ──

class TestRunBacktest:
    def test_no_data_returns_zero(self, tmp_path):
        """レースデータがない場合は試行回数0。"""
        # data/races ディレクトリを作成するが空
        (tmp_path / "data" / "races").mkdir(parents=True)
        rec = {"name": "test", "scope": {}}
        result = run_backtest(rec, BetType.WIN, base_path=tmp_path)
        assert result["試行回数"] == 0
        assert result["回収率"] == 0.0
        assert result["的中率"] == 0.0
        assert result["年別推移"] == []

    def test_backtest_with_data(self, tmp_path):
        """レースデータありの場合のバックテスト。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        # レースを保存
        race = Race(
            race_id="R001", date=date(2024, 6, 1), venue="東京",
            distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上",
        )
        with open(races_dir / "races.json", "w") as f:
            json.dump([race.to_dict()], f)

        # 出走馬を保存（1着: 馬A(斤量55), 2着: 馬B(斤量58)）
        entries = [
            HorseEntry(
                entry_id="E1", race_id="R001", frame_number=1, horse_number=1,
                horse_name="馬A", weight=55.0, previous_order=1,
                final_odds=5.0, result_order=1,
            ),
            HorseEntry(
                entry_id="E2", race_id="R001", frame_number=2, horse_number=2,
                horse_name="馬B", weight=58.0, previous_order=3,
                final_odds=10.0, result_order=2,
            ),
        ]
        with open(races_dir / "entries_R001.json", "w") as f:
            json.dump([e.to_dict() for e in entries], f)

        # 斤量57以下の Must で馬A のみ通過、Prefer で斤量軽い → 馬A を選択
        rec = {
            "name": "test",
            "scope": {"venues": ["東京"], "distance_min": 1400, "distance_max": 1800,
                      "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]},
            "must": {"blocks": [{"conditions": [{"category": "斤量", "operator": "le", "value": "57"}]}]},
            "prefer_avoid": {"prefer": [{"order": 1, "criteria": {"category": "斤量", "operator": "le", "value": "56"}}], "avoid": []},
        }
        result = run_backtest(rec, BetType.WIN, base_path=tmp_path)
        assert result["試行回数"] == 1
        assert result["的中率"] == 100.0
        # 回収率: (100 * 5.0) / 100 * 100 = 500%
        assert result["回収率"] == 500.0
        assert result["最大連敗数"] == 0

    def test_backtest_place_bet(self, tmp_path):
        """複勝ベットのテスト。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        race = Race(
            race_id="R001", date=date(2024, 6, 1), venue="東京",
            distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上",
        )
        with open(races_dir / "races.json", "w") as f:
            json.dump([race.to_dict()], f)

        entries = [
            HorseEntry(
                entry_id="E1", race_id="R001", frame_number=1, horse_number=1,
                horse_name="馬A", weight=55.0, final_odds=6.0, result_order=3,
            ),
        ]
        with open(races_dir / "entries_R001.json", "w") as f:
            json.dump([e.to_dict() for e in entries], f)

        rec = {"name": "test", "scope": {"venues": ["東京"], "distances": ["マイル"],
               "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}}
        result = run_backtest(rec, BetType.PLACE, base_path=tmp_path)
        assert result["試行回数"] == 1
        assert result["的中率"] == 100.0
        # 複勝回収: 100 * (6.0 / 2.6) ≈ 230.77 → 回収率 230.8%
        assert result["回収率"] == 230.8

    def test_backtest_rejects_incapable_logic(self, tmp_path):
        """シミュレーション不可ロジックではバックテストが実行できない。"""
        (tmp_path / "data" / "races").mkdir(parents=True)
        rec = {"name": "test", "custom_vars": {"variables": [{"name": "気分", "var_type": "真偽値"}]}}
        with pytest.raises(ValueError, match="シミュレーション不可"):
            run_backtest(rec, BetType.WIN, base_path=tmp_path)

    def test_backtest_losing_streak(self, tmp_path):
        """連敗数のカウントが正しいことを確認。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        # 3レース分用意: すべて不的中（選んだ馬が2着以下）
        races = []
        for i in range(1, 4):
            r = Race(
                race_id=f"R{i:03d}", date=date(2024, i, 1), venue="東京",
                distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上",
            )
            races.append(r)
            entries = [
                HorseEntry(
                    entry_id=f"E{i}", race_id=f"R{i:03d}", frame_number=1, horse_number=1,
                    horse_name="馬A", weight=55.0, final_odds=5.0, result_order=2,
                ),
            ]
            with open(races_dir / f"entries_R{i:03d}.json", "w") as f:
                json.dump([e.to_dict() for e in entries], f)

        with open(races_dir / "races.json", "w") as f:
            json.dump([r.to_dict() for r in races], f)

        rec = {"name": "test", "scope": {"venues": ["東京"], "distances": ["マイル"],
               "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}}
        result = run_backtest(rec, BetType.WIN, base_path=tmp_path)
        assert result["試行回数"] == 3
        assert result["的中率"] == 0.0
        assert result["最大連敗数"] == 3
        assert result["回収率"] == 0.0

    def test_backtest_drawdown(self, tmp_path):
        """最大ドローダウンの計算が正しいことを確認。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        # レース1: 的中（利益 +400）→ レース2: 不的中（-100）→ レース3: 不的中（-100）
        races_data = [
            {"race_id": "R001", "date": "2024-01-01", "venue": "東京", "distance": 1600,
             "surface": "芝", "race_class": "3勝", "age_condition": "3歳以上"},
            {"race_id": "R002", "date": "2024-02-01", "venue": "東京", "distance": 1600,
             "surface": "芝", "race_class": "3勝", "age_condition": "3歳以上"},
            {"race_id": "R003", "date": "2024-03-01", "venue": "東京", "distance": 1600,
             "surface": "芝", "race_class": "3勝", "age_condition": "3歳以上"},
        ]
        with open(races_dir / "races.json", "w") as f:
            json.dump(races_data, f)

        # レース1: 1着、オッズ5倍
        with open(races_dir / "entries_R001.json", "w") as f:
            json.dump([{"entry_id": "E1", "race_id": "R001", "frame_number": 1,
                        "horse_number": 1, "horse_name": "馬A", "weight": 55.0,
                        "final_odds": 5.0, "result_order": 1}], f)
        # レース2: 4着
        with open(races_dir / "entries_R002.json", "w") as f:
            json.dump([{"entry_id": "E2", "race_id": "R002", "frame_number": 1,
                        "horse_number": 1, "horse_name": "馬A", "weight": 55.0,
                        "final_odds": 3.0, "result_order": 4}], f)
        # レース3: 5着
        with open(races_dir / "entries_R003.json", "w") as f:
            json.dump([{"entry_id": "E3", "race_id": "R003", "frame_number": 1,
                        "horse_number": 1, "horse_name": "馬A", "weight": 55.0,
                        "final_odds": 2.0, "result_order": 5}], f)

        rec = {"name": "test", "scope": {"venues": ["東京"], "distances": ["マイル"],
               "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}}
        result = run_backtest(rec, BetType.WIN, base_path=tmp_path)
        assert result["試行回数"] == 3
        assert result["的中率"] == round(1 / 3 * 100, 1)
        # ピーク利益: 500-100=400, その後 400-100=300, 300-100=200 → ドローダウン: 400-200=200
        assert result["最大ドローダウン"] == 200.0
        assert result["最大連敗数"] == 2

    def test_backtest_yearly_breakdown(self, tmp_path):
        """年別推移が正しく計算されることを確認。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        races = [
            Race(race_id="R001", date=date(2023, 6, 1), venue="東京",
                 distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上"),
            Race(race_id="R002", date=date(2024, 6, 1), venue="東京",
                 distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上"),
        ]
        with open(races_dir / "races.json", "w") as f:
            json.dump([r.to_dict() for r in races], f)

        # 2023年: 的中
        with open(races_dir / "entries_R001.json", "w") as f:
            json.dump([HorseEntry(
                entry_id="E1", race_id="R001", frame_number=1, horse_number=1,
                horse_name="馬A", weight=55.0, final_odds=4.0, result_order=1,
            ).to_dict()], f)
        # 2024年: 不的中
        with open(races_dir / "entries_R002.json", "w") as f:
            json.dump([HorseEntry(
                entry_id="E2", race_id="R002", frame_number=1, horse_number=1,
                horse_name="馬B", weight=55.0, final_odds=3.0, result_order=5,
            ).to_dict()], f)

        rec = {"name": "test", "scope": {"venues": ["東京"], "distances": ["マイル"],
               "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}}
        result = run_backtest(rec, BetType.WIN, data_years=5, base_path=tmp_path)
        yearly = result["年別推移"]
        assert len(yearly) == 2
        # 2023年: 1試行、的中率100%、回収率400%
        y2023 = next(y for y in yearly if y["年"] == 2023)
        assert y2023["試行回数"] == 1
        assert y2023["的中率"] == 100.0
        assert y2023["回収率"] == 400.0
        # 2024年: 1試行、的中率0%、回収率0%
        y2024 = next(y for y in yearly if y["年"] == 2024)
        assert y2024["試行回数"] == 1
        assert y2024["的中率"] == 0.0
        assert y2024["回収率"] == 0.0

    def test_backtest_scope_filters_races(self, tmp_path):
        """Scope 条件でレースがフィルタされることを確認。"""
        races_dir = tmp_path / "data" / "races"
        races_dir.mkdir(parents=True)

        races = [
            Race(race_id="R001", date=date(2024, 6, 1), venue="東京",
                 distance=1600, surface="芝", race_class="3勝", age_condition="3歳以上"),
            Race(race_id="R002", date=date(2024, 7, 1), venue="阪神",
                 distance=2000, surface="ダート", race_class="2勝", age_condition="3歳以上"),
        ]
        with open(races_dir / "races.json", "w") as f:
            json.dump([r.to_dict() for r in races], f)

        for rid in ["R001", "R002"]:
            with open(races_dir / f"entries_{rid}.json", "w") as f:
                json.dump([HorseEntry(
                    entry_id=f"E_{rid}", race_id=rid, frame_number=1, horse_number=1,
                    horse_name="馬A", weight=55.0, final_odds=5.0, result_order=1,
                ).to_dict()], f)

        # 東京芝マイルのみ対象
        rec = {"name": "test", "scope": {"venues": ["東京"], "distances": ["マイル"],
               "surface": ["芝"], "race_class": ["3勝"], "age_condition": ["3歳以上"]}}
        result = run_backtest(rec, BetType.WIN, base_path=tmp_path)
        # R001 のみマッチ
        assert result["試行回数"] == 1
