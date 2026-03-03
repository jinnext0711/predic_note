"""
レース分析エンジン (race_analyzer.py) のテスト。

RaceAnalyzer の analyze_race を中心に、スコア算出、グレード変換、
印付け、ペース予想、エッジケースを検証する。
"""
import pytest

from analysis.race_analyzer import (
    RaceAnalyzer,
    RaceAnalysis,
    HorseEvaluation,
    _raw_to_grade,
    _parse_time_str,
    _distance_category,
    _safe_div,
    _infer_running_style,
    SCORE_WEIGHTS,
)
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
    horse_id: str = None,
    jockey_id: str = None,
    trainer_id: str = None,
    frame_number: int = None,
) -> UpcomingHorseEntry:
    """テスト用エントリを生成する。"""
    if horse_id is None:
        horse_id = f"horse_{horse_number:04d}"
    if jockey_id is None:
        jockey_id = f"jockey_{horse_number:04d}"
    if trainer_id is None:
        trainer_id = f"trainer_{horse_number:04d}"
    if frame_number is None:
        frame_number = (horse_number + 1) // 2
    return UpcomingHorseEntry(
        entry_id=f"race01_{horse_number:02d}",
        race_id="race01",
        frame_number=frame_number,
        horse_number=horse_number,
        horse_name=horse_name,
        horse_id=horse_id,
        sex_age="牡4",
        weight_carry=57.0,
        jockey_name=f"騎手{horse_number}",
        jockey_id=jockey_id,
        trainer_name=f"調教師{horse_number}",
        trainer_id=trainer_id,
    )


def _make_past_record(
    result_order: int = 1,
    last_3f: float = 34.0,
    race_date: str = "2025-01-01",
    position_at_corners: str = "3-3-2-1",
    horse_weight: str = "480(+2)",
    time_str: str = "2:01.5",
) -> PastRaceRecord:
    """テスト用の過去成績を生成する。"""
    return PastRaceRecord(
        race_date=race_date,
        venue="中山",
        race_name="テスト",
        surface="芝",
        distance=2000,
        weather="晴",
        track_condition="良",
        horse_number=1,
        result_order=result_order,
        time_str=time_str,
        last_3f=last_3f,
        odds=5.0,
        popularity=2,
        weight_carry=57.0,
        horse_weight=horse_weight,
        pace="M",
        position_at_corners=position_at_corners,
    )


def _make_history(
    horse_id: str = "horse_0001",
    wins: int = 5,
    total_runs: int = 20,
    running_style: str = "",
    num_recent: int = 3,
    recent_order: int = 1,
    recent_last_3f: float = 34.0,
    recent_position: str = "3-3-2-1",
) -> HorseHistory:
    """テスト用 HorseHistory を生成する。"""
    recent = []
    for i in range(num_recent):
        rec = _make_past_record(
            result_order=recent_order + i,
            last_3f=recent_last_3f + i * 0.3,
            race_date=f"2025-01-{10 - i:02d}",
            position_at_corners=recent_position,
        )
        recent.append(rec)
    return HorseHistory(
        horse_id=horse_id,
        horse_name="テスト馬",
        total_runs=total_runs,
        wins=wins,
        places=4,
        shows=3,
        recent_results=recent,
        surface_stats={"芝": {"runs": 15, "wins": 4, "places": 3, "shows": 2}},
        distance_stats={"1800-2200": {"runs": 10, "wins": 3, "places": 2, "shows": 1}},
        venue_stats={"中山": {"runs": 8, "wins": 2, "places": 2, "shows": 1}},
        running_style=running_style,
    )


def _make_jockey_stats(jockey_id: str = "jockey_0001") -> JockeyStats:
    """テスト用騎手データを生成する。"""
    return JockeyStats(
        jockey_id=jockey_id,
        jockey_name="テスト騎手",
        year_runs=150,
        year_wins=25,
        year_win_rate=0.167,
        year_place_rate=0.30,
        year_show_rate=0.40,
        venue_stats={"中山": {"runs": 30, "win_rate": 0.15, "show_rate": 0.35}},
    )


def _make_trainer_stats(trainer_id: str = "trainer_0001") -> TrainerStats:
    """テスト用調教師データを生成する。"""
    return TrainerStats(
        trainer_id=trainer_id,
        trainer_name="テスト調教師",
        year_runs=80,
        year_wins=12,
        year_win_rate=0.15,
        year_show_rate=0.30,
    )


def _make_race_data(
    num_entries: int = 6,
    surface: str = "芝",
    distance: int = 2000,
    venue: str = "中山",
    include_odds: bool = False,
) -> UpcomingRaceWithEntries:
    """テスト用レースデータを生成する。"""
    entries = []
    horse_histories = {}
    jockey_stats = {}
    trainer_stats = {}

    for i in range(num_entries):
        hn = i + 1
        entry = _make_entry(horse_number=hn, horse_name=f"馬{hn}")
        entries.append(entry)
        # 実力に差をつける（wins を変える）
        horse_histories[entry.horse_id] = _make_history(
            horse_id=entry.horse_id,
            wins=max(1, 8 - i),
            recent_order=1 + i,
            recent_last_3f=33.5 + i * 0.5,
            recent_position=f"{1 + i}-{1 + i}-{1 + i}-{1 + i}",
        )
        jockey_stats[entry.jockey_id] = _make_jockey_stats(entry.jockey_id)
        trainer_stats[entry.trainer_id] = _make_trainer_stats(entry.trainer_id)

    odds = None
    if include_odds:
        win_odds = {i + 1: 2.0 + i * 3.0 for i in range(num_entries)}
        place_odds = {i + 1: (1.1 + i * 0.5, 1.5 + i * 1.0) for i in range(num_entries)}
        odds = OddsData(
            race_id="race01",
            win_odds=win_odds,
            place_odds=place_odds,
        )

    return UpcomingRaceWithEntries(
        race_id="race01",
        race_name="テスト重賞",
        race_date="2025-01-01",
        venue=venue,
        surface=surface,
        distance=distance,
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
# ユーティリティ関数のテスト
# ===========================================================================


class TestUtilityFunctions:
    """ユーティリティ関数のテスト。"""

    @pytest.mark.parametrize("raw, expected", [
        (100.0, "A"),
        (85.0, "A"),
        (80.0, "A"),
        (79.9, "B"),
        (60.0, "B"),
        (40.0, "C"),
        (20.0, "D"),
        (10.0, "E"),   # 閾値20未満はE
        (0.0, "E"),
        (-5.0, "E"),   # 範囲外はクランプされる
        (150.0, "A"),   # 範囲外はクランプされる
    ])
    def test_raw_to_grade(self, raw, expected):
        """生スコアからグレードへの変換が正しいこと。"""
        assert _raw_to_grade(raw) == expected

    @pytest.mark.parametrize("time_str, expected", [
        ("1:34.5", 94.5),
        ("2:01.5", 121.5),
        ("0:58.3", 58.3),
        (None, None),
        ("", None),
        ("invalid", None),
    ])
    def test_parse_time_str(self, time_str, expected):
        """タイム文字列の秒変換が正しいこと。"""
        result = _parse_time_str(time_str)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected)

    @pytest.mark.parametrize("distance, expected", [
        (1200, "1200-1400"),
        (1400, "1200-1400"),
        (1600, "1600-1800"),
        (2000, "1800-2200"),
        (2400, "2200-2600"),
        (3000, "2600-3600"),
        (800, "1200-1400"),     # 範囲外
        (5000, "2600-3600"),    # 範囲外
    ])
    def test_distance_category(self, distance, expected):
        """距離カテゴリ変換が正しいこと。"""
        assert _distance_category(distance) == expected

    def test_safe_div(self):
        """ゼロ除算が安全に処理されること。"""
        assert _safe_div(10, 2) == 5.0
        assert _safe_div(10, 0) == 0.0
        assert _safe_div(10, 0, default=99.0) == 99.0


# ===========================================================================
# 脚質推定のテスト
# ===========================================================================


class TestInferRunningStyle:
    """脚質推定関数のテスト。"""

    def test_preset_style_returned(self):
        """running_style が設定されていればそのまま返されること。"""
        history = _make_history(running_style="逃げ")
        assert _infer_running_style(history) == "逃げ"

    def test_infer_from_front_positions(self):
        """先頭付近の通過順位 → 逃げ/先行と推定されること。"""
        history = _make_history(running_style="", recent_position="1-1-1-1")
        style = _infer_running_style(history)
        assert style in ("逃げ", "先行")

    def test_infer_from_back_positions(self):
        """後方の通過順位 → 差し/追込と推定されること。"""
        history = _make_history(running_style="", recent_position="10-10-8-5")
        style = _infer_running_style(history)
        assert style in ("差し", "追込")

    def test_no_recent_results_defaults(self):
        """成績なしの場合はデフォルト「差し」になること。"""
        history = _make_history(running_style="", num_recent=0)
        assert _infer_running_style(history) == "差し"


# ===========================================================================
# RaceAnalyzer のテスト
# ===========================================================================


class TestRaceAnalyzer:
    """RaceAnalyzer のメインテスト。"""

    @pytest.fixture
    def analyzer(self) -> RaceAnalyzer:
        """分析エンジンのインスタンス。"""
        return RaceAnalyzer()

    def test_analyze_race_basic(self, analyzer):
        """基本的な分析が成功し、必要なフィールドが揃うこと。"""
        race = _make_race_data(num_entries=6)
        result = analyzer.analyze_race(race)

        assert isinstance(result, RaceAnalysis)
        assert result.race_id == "race01"
        assert result.race_name == "テスト重賞"
        assert len(result.evaluations) == 6
        assert result.pace_prediction in ("ハイペース", "ミドルペース", "スローペース")
        assert result.volatility in ("堅い", "上位拮抗", "波乱含み", "大波乱")
        assert result.confidence in ("A", "B", "C", "D")

    def test_evaluations_sorted_by_index(self, analyzer):
        """評価が総合指数の降順でソートされていること。"""
        race = _make_race_data(num_entries=6)
        result = analyzer.analyze_race(race)
        indices = [e.total_index for e in result.evaluations]
        assert indices == sorted(indices, reverse=True)

    def test_grades_are_valid(self, analyzer):
        """すべてのグレードが A-E の範囲内であること。"""
        race = _make_race_data(num_entries=4)
        result = analyzer.analyze_race(race)
        valid_grades = {"A", "B", "C", "D", "E"}
        for ev in result.evaluations:
            assert ev.ability_score in valid_grades
            assert ev.condition_score in valid_grades
            assert ev.jockey_score in valid_grades
            assert ev.pace_score in valid_grades
            assert ev.bloodline_score in valid_grades
            assert ev.stable_score in valid_grades

    def test_total_index_range(self, analyzer):
        """総合指数が 0-100 の範囲内であること。"""
        race = _make_race_data(num_entries=6)
        result = analyzer.analyze_race(race)
        for ev in result.evaluations:
            assert 0.0 <= ev.total_index <= 100.0

    def test_mark_assignment(self, analyzer):
        """印が正しく割り当てられること（◎1頭、○1頭、▲1頭）。"""
        race = _make_race_data(num_entries=8)
        result = analyzer.analyze_race(race)

        marks = [e.mark for e in result.evaluations]
        assert marks.count("◎") == 1, "◎は1頭のみ"
        assert marks.count("○") == 1, "○は1頭のみ"
        assert marks.count("▲") == 1, "▲は1頭のみ"

    def test_honmei_is_top_index(self, analyzer):
        """◎本命が指数1位の馬であること。"""
        race = _make_race_data(num_entries=6)
        result = analyzer.analyze_race(race)
        assert result.honmei is not None
        assert result.honmei.mark == "◎"
        # 本命は evaluations[0] と同じはず
        assert result.honmei.horse_number == result.evaluations[0].horse_number

    def test_taikou_and_tanana_assigned(self, analyzer):
        """○対抗と▲単穴が設定されていること（3頭以上）。"""
        race = _make_race_data(num_entries=5)
        result = analyzer.analyze_race(race)
        assert result.taikou is not None
        assert result.taikou.mark == "○"
        assert result.tanana is not None
        assert result.tanana.mark == "▲"

    def test_to_dict_and_from_dict(self, analyzer):
        """分析結果のラウンドトリップ。"""
        race = _make_race_data(num_entries=4)
        result = analyzer.analyze_race(race)
        d = result.to_dict()
        restored = RaceAnalysis.from_dict(d)
        assert restored.race_id == result.race_id
        assert len(restored.evaluations) == len(result.evaluations)
        assert restored.pace_prediction == result.pace_prediction

    def test_strengths_and_weaknesses(self, analyzer):
        """強み・弱みリストが生成されること。"""
        race = _make_race_data(num_entries=4)
        result = analyzer.analyze_race(race)
        # 最低1頭は強みか弱みを持つはず
        has_any = any(
            len(e.strengths) > 0 or len(e.weaknesses) > 0
            for e in result.evaluations
        )
        assert has_any


# ===========================================================================
# ペース予想のテスト
# ===========================================================================


class TestPacePrediction:
    """ペース予想のテスト。"""

    @pytest.fixture
    def analyzer(self) -> RaceAnalyzer:
        return RaceAnalyzer()

    def test_slow_pace_all_sashi(self, analyzer):
        """全馬が差し脚質 → スローペースと予想されること。"""
        race = _make_race_data(num_entries=4)
        # 全馬の脚質を差しに設定
        for hid in race.horse_histories:
            race.horse_histories[hid].running_style = "差し"
        result = analyzer.analyze_race(race)
        assert result.pace_prediction == "スローペース"

    def test_high_pace_many_nige(self, analyzer):
        """逃げ馬が多い → ハイペースと予想されること。"""
        race = _make_race_data(num_entries=6)
        for i, hid in enumerate(race.horse_histories):
            if i < 4:
                race.horse_histories[hid].running_style = "逃げ"
            else:
                race.horse_histories[hid].running_style = "差し"
        result = analyzer.analyze_race(race)
        assert result.pace_prediction == "ハイペース"


# ===========================================================================
# エッジケースのテスト
# ===========================================================================


class TestEdgeCases:
    """エッジケースのテスト。"""

    @pytest.fixture
    def analyzer(self) -> RaceAnalyzer:
        return RaceAnalyzer()

    def test_empty_race(self, analyzer):
        """出走馬0頭の場合、空の分析結果が返されること。"""
        race = _make_race_data(num_entries=0)
        # entries を空にする（_make_race_data は entries を生成するため手動で空にする）
        race.entries = []
        result = analyzer.analyze_race(race)
        assert isinstance(result, RaceAnalysis)
        assert result.evaluations == []
        assert result.honmei is None
        assert result.taikou is None
        assert result.confidence == "D"

    def test_single_horse(self, analyzer):
        """1頭のみのレースで分析が成功すること。"""
        race = _make_race_data(num_entries=1)
        result = analyzer.analyze_race(race)
        assert len(result.evaluations) == 1
        assert result.evaluations[0].mark == "◎"
        assert result.honmei is not None
        # 対抗以下は None
        assert result.taikou is None

    def test_no_horse_history(self, analyzer):
        """馬歴がない場合でも分析が成功すること（新馬戦等）。"""
        race = _make_race_data(num_entries=4)
        # 全馬の戦績を消す
        race.horse_histories = {}
        result = analyzer.analyze_race(race)
        assert len(result.evaluations) == 4
        # 新馬は中間評価 (C) が多いはず
        for ev in result.evaluations:
            assert ev.ability_score == "C"

    def test_no_jockey_stats(self, analyzer):
        """騎手データがない場合でも分析が成功すること。"""
        race = _make_race_data(num_entries=4)
        race.jockey_stats = {}
        result = analyzer.analyze_race(race)
        assert len(result.evaluations) == 4

    def test_with_odds_data(self, analyzer):
        """オッズデータありの場合、期待値ギャップ分析が行われること。"""
        race = _make_race_data(num_entries=6, include_odds=True)
        result = analyzer.analyze_race(race)
        # オッズデータがあるので value_horses や danger_popular が算出可能
        # （必ずしも結果があるとは限らないが、エラーにならないこと）
        assert isinstance(result.value_horses, list)
        assert isinstance(result.danger_popular, list)


# ===========================================================================
# コース傾向判定のテスト
# ===========================================================================


class TestCourseAssessment:
    """コース傾向判定のテスト。"""

    @pytest.fixture
    def analyzer(self) -> RaceAnalyzer:
        return RaceAnalyzer()

    def test_short_distance_inner_advantage(self, analyzer):
        """短距離レースは内枠有利と判定されること。"""
        race = _make_race_data(distance=1200)
        result = analyzer.analyze_race(race)
        assert result.favorable_frame == "内枠有利"

    def test_long_distance_flat(self, analyzer):
        """長距離レースはフラットと判定されること。"""
        race = _make_race_data(distance=2500, venue="東京")
        result = analyzer.analyze_race(race)
        assert result.favorable_frame == "フラット"

    def test_turf_track_condition_comment(self, analyzer):
        """芝コースの馬場状態コメントが含まれること。"""
        race = _make_race_data(surface="芝")
        result = analyzer.analyze_race(race)
        assert "芝" in result.track_condition_impact

    def test_dirt_track_condition_comment(self, analyzer):
        """ダートコースの馬場状態コメントが含まれること。"""
        race = _make_race_data(surface="ダート")
        result = analyzer.analyze_race(race)
        assert "ダート" in result.track_condition_impact
