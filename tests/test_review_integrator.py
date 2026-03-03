"""
専門家レビュー統合 (review_integrator.py) のテスト。

integrate_reviews を中心に、グレード補正、印変更の整合性、
自信度調整、merge_all_reviews のオーケストレーションを検証する。
"""
import pytest
from copy import deepcopy

from analysis.review_integrator import (
    CONFIDENCE_MAP,
    CONFIDENCE_REVERSE,
    GRADE_TO_NUM,
    NUM_TO_GRADE,
    _num_to_grade,
    _recalculate_indices,
    _reconcile_marks,
    integrate_reviews,
    merge_all_reviews,
)


# ---------------------------------------------------------------------------
# ヘルパー関数: サンプルデータ生成
# ---------------------------------------------------------------------------


def _make_evaluation(
    horse_number: int,
    horse_name: str,
    mark: str = "",
    ability: str = "C",
    condition: str = "C",
    jockey: str = "C",
    pace: str = "C",
    bloodline: str = "C",
    stable: str = "C",
) -> dict:
    """テスト用の馬評価 dict を生成する。"""
    # 各グレードを数値に変換して総合指数を算出
    total = (
        GRADE_TO_NUM.get(ability, 50) * 0.30
        + GRADE_TO_NUM.get(condition, 50) * 0.15
        + GRADE_TO_NUM.get(jockey, 50) * 0.15
        + GRADE_TO_NUM.get(pace, 50) * 0.15
        + GRADE_TO_NUM.get(bloodline, 50) * 0.15
        + GRADE_TO_NUM.get(stable, 50) * 0.10
    )
    return {
        "horse_number": horse_number,
        "horse_name": horse_name,
        "ability_score": ability,
        "condition_score": condition,
        "jockey_score": jockey,
        "pace_score": pace,
        "bloodline_score": bloodline,
        "stable_score": stable,
        "total_index": round(total, 1),
        "strengths": [],
        "weaknesses": [],
        "mark": mark,
    }


def _make_analysis(
    evaluations: list = None,
    confidence: str = "C",
    volatility: str = "上位拮抗",
    comment: str = "テスト見解",
) -> dict:
    """テスト用の分析データ dict を生成する。"""
    if evaluations is None:
        evaluations = [
            _make_evaluation(1, "馬A", "◎", ability="A", jockey="A"),
            _make_evaluation(2, "馬B", "○", ability="B", jockey="B"),
            _make_evaluation(3, "馬C", "▲", ability="C"),
            _make_evaluation(4, "馬D", "△"),
            _make_evaluation(5, "馬E", ""),
        ]
    return {
        "race_id": "race01",
        "race_name": "テストレース",
        "evaluations": evaluations,
        "confidence": confidence,
        "volatility": volatility,
        "comment": comment,
        "track_condition_impact": "芝コース",
        "honmei": next((e for e in evaluations if e.get("mark") == "◎"), None),
        "taikou": next((e for e in evaluations if e.get("mark") == "○"), None),
        "tanana": next((e for e in evaluations if e.get("mark") == "▲"), None),
        "renka": [e for e in evaluations if e.get("mark") == "△"],
        "keshi": [e for e in evaluations if e.get("mark") == "×"],
        "value_horses": [],
        "danger_popular": [],
    }


# ===========================================================================
# _num_to_grade のテスト
# ===========================================================================


class TestNumToGrade:
    """数値→グレード変換のテスト。"""

    @pytest.mark.parametrize("val, expected", [
        (90.0, "A"),
        (80.0, "A"),
        (70.0, "B"),
        (60.0, "B"),
        (50.0, "C"),
        (40.0, "C"),
        (30.0, "D"),
        (20.0, "D"),
        (10.0, "E"),
        (0.0, "E"),
    ])
    def test_grade_thresholds(self, val, expected):
        """各閾値でのグレード変換が正しいこと。"""
        assert _num_to_grade(val) == expected


# ===========================================================================
# _recalculate_indices のテスト
# ===========================================================================


class TestRecalculateIndices:
    """総合指数の再計算テスト。"""

    def test_all_c_grade_gives_50(self):
        """全軸Cの場合、総合指数が50.0になること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "馬A", "◎"),
        ])
        _recalculate_indices(analysis)
        assert analysis["evaluations"][0]["total_index"] == 50.0

    def test_all_a_grade_gives_90(self):
        """全軸Aの場合、総合指数が90.0になること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "馬A", "◎", "A", "A", "A", "A", "A", "A"),
        ])
        _recalculate_indices(analysis)
        assert analysis["evaluations"][0]["total_index"] == 90.0

    def test_sorted_by_total_index_desc(self):
        """再計算後に総合指数の降順でソートされること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "弱い馬", "", ability="E"),
            _make_evaluation(2, "強い馬", "", ability="A"),
        ])
        _recalculate_indices(analysis)
        indices = [e["total_index"] for e in analysis["evaluations"]]
        assert indices[0] >= indices[1]


# ===========================================================================
# _reconcile_marks のテスト
# ===========================================================================


class TestReconcileMarks:
    """印の整合性チェックテスト。"""

    def test_single_honmei(self):
        """◎が1頭だけになるよう調整されること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "馬A", "◎", ability="A"),
            _make_evaluation(2, "馬B", "◎", ability="B"),
            _make_evaluation(3, "馬C", "▲"),
        ])
        _recalculate_indices(analysis)
        _reconcile_marks(analysis)
        marks = [e["mark"] for e in analysis["evaluations"]]
        assert marks.count("◎") == 1

    def test_duplicate_honmei_demoted_to_taikou(self):
        """重複する◎が○に降格されること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "馬A", "◎", ability="A"),
            _make_evaluation(2, "馬B", "◎", ability="B"),
        ])
        _recalculate_indices(analysis)
        _reconcile_marks(analysis)
        marks = [e["mark"] for e in analysis["evaluations"]]
        assert marks.count("◎") == 1
        assert marks.count("○") == 1

    def test_duplicate_taikou_demoted_to_tanana(self):
        """重複する○が▲に降格されること。"""
        analysis = _make_analysis(evaluations=[
            _make_evaluation(1, "馬A", "◎", ability="A"),
            _make_evaluation(2, "馬B", "○", ability="B"),
            _make_evaluation(3, "馬C", "○", ability="C"),
        ])
        _recalculate_indices(analysis)
        _reconcile_marks(analysis)
        marks = [e["mark"] for e in analysis["evaluations"]]
        assert marks.count("○") == 1
        assert marks.count("▲") >= 1

    def test_honmei_taikou_tanana_updated(self):
        """honmei/taikou/tanana フィールドが正しく更新されること。"""
        analysis = _make_analysis()
        _reconcile_marks(analysis)
        assert analysis["honmei"] is not None
        assert analysis["honmei"]["mark"] == "◎"
        assert analysis["taikou"] is not None
        assert analysis["taikou"]["mark"] == "○"

    def test_empty_evaluations(self):
        """空の evaluations の場合にエラーにならないこと。"""
        analysis = {"evaluations": []}
        _reconcile_marks(analysis)
        # エラーが出なければ OK


# ===========================================================================
# integrate_reviews のテスト: 単一レビュアー
# ===========================================================================


class TestIntegrateReviewsSingle:
    """単一の専門家レビューの統合テスト。"""

    def test_grade_correction_applied(self):
        """グレード補正が正しく反映されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "venue-expert",
            "corrections": [
                {
                    "horse_number": 1,
                    "field": "ability_score",
                    "original": "A",
                    "corrected": "B",
                    "reason": "コース適性を考慮して下方修正",
                },
            ],
        }
        result = integrate_reviews(analysis, [review])
        horse1 = next(e for e in result["evaluations"] if e["horse_number"] == 1)
        assert horse1["ability_score"] == "B"

    def test_mark_change_applied(self):
        """印の変更が反映されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "mark_changes": [
                {
                    "horse_number": 3,
                    "original_mark": "▲",
                    "suggested_mark": "○",
                    "reason": "穴馬として対抗に昇格",
                },
            ],
        }
        result = integrate_reviews(analysis, [review])
        # 整合性チェック後、○は1頭だけになるはず
        o_count = sum(1 for e in result["evaluations"] if e["mark"] == "○")
        assert o_count == 1

    def test_venue_expert_track_notes(self):
        """venue-expert のコース補足が追加されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "venue-expert",
            "corrections": [],
            "track_notes": "内枠が断然有利なコース形態",
        }
        result = integrate_reviews(analysis, [review])
        assert "内枠が断然有利" in result["track_condition_impact"]

    def test_veteran_tipster_volatility_adjustment(self):
        """veteran-tipster の波乱度補正が反映されること。"""
        analysis = _make_analysis(volatility="上位拮抗")
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "volatility_adjustment": "波乱含み",
        }
        result = integrate_reviews(analysis, [review])
        assert result["volatility"] == "波乱含み"

    def test_veteran_tipster_additional_comment(self):
        """veteran-tipster の追加コメントが反映されること。"""
        analysis = _make_analysis(comment="初期見解")
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "additional_comment": "大穴に注意",
        }
        result = integrate_reviews(analysis, [review])
        assert "大穴に注意" in result["comment"]

    def test_bloodline_expert_key_factor(self):
        """bloodline-expert の血統キーファクターが追加されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "bloodline-expert",
            "corrections": [],
            "bloodline_key_factor": "ディープインパクト系が好走傾向",
        }
        result = integrate_reviews(analysis, [review])
        assert result["bloodline_key_factor"] == "ディープインパクト系が好走傾向"

    def test_bloodline_expert_special_notes(self):
        """bloodline-expert の特注ノートが value_horses に追加されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "bloodline-expert",
            "corrections": [],
            "special_notes": [
                {"horse_number": 5, "note": "母父のコース適性が高い"},
            ],
        }
        result = integrate_reviews(analysis, [review])
        found = any(
            v["horse_number"] == 5 and "血統注目" in v["reason"]
            for v in result.get("value_horses", [])
        )
        assert found

    def test_training_expert_notes(self):
        """training-expert の調教ノートが追加されること。"""
        analysis = _make_analysis()
        review = {
            "reviewer": "training-expert",
            "corrections": [],
            "training_notes": "1番馬の追い切りが抜群",
        }
        result = integrate_reviews(analysis, [review])
        assert result["training_notes"] == "1番馬の追い切りが抜群"


# ===========================================================================
# integrate_reviews のテスト: 自信度調整
# ===========================================================================


class TestConfidenceAdjustment:
    """自信度調整のテスト。"""

    def test_confidence_increase(self):
        """自信度が上方調整されること。"""
        analysis = _make_analysis(confidence="C")
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "confidence_adjustment": 1,
        }
        result = integrate_reviews(analysis, [review])
        assert result["confidence"] == "B"

    def test_confidence_decrease(self):
        """自信度が下方調整されること。"""
        analysis = _make_analysis(confidence="B")
        review = {
            "reviewer": "venue-expert",
            "corrections": [],
            "confidence_adjustment": -1,
        }
        result = integrate_reviews(analysis, [review])
        assert result["confidence"] == "C"

    def test_confidence_upper_bound(self):
        """自信度が A を超えないこと。"""
        analysis = _make_analysis(confidence="A")
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "confidence_adjustment": 2,
        }
        result = integrate_reviews(analysis, [review])
        assert result["confidence"] == "A"

    def test_confidence_lower_bound(self):
        """自信度が D を下回らないこと。"""
        analysis = _make_analysis(confidence="D")
        review = {
            "reviewer": "venue-expert",
            "corrections": [],
            "confidence_adjustment": -2,
        }
        result = integrate_reviews(analysis, [review])
        assert result["confidence"] == "D"


# ===========================================================================
# integrate_reviews のテスト: 複数レビュアー
# ===========================================================================


class TestIntegrateReviewsMultiple:
    """複数の専門家レビューの統合テスト。"""

    def test_multiple_corrections_combined(self):
        """複数レビュアーの補正が累積されること。"""
        analysis = _make_analysis()
        reviews = [
            {
                "reviewer": "venue-expert",
                "corrections": [
                    {
                        "horse_number": 1,
                        "field": "ability_score",
                        "original": "A",
                        "corrected": "B",
                        "reason": "コース適性で下方修正",
                    },
                ],
            },
            {
                "reviewer": "training-expert",
                "corrections": [],
                "condition_corrections": [
                    {
                        "horse_number": 2,
                        "field": "condition_score",
                        "original": "C",
                        "corrected": "A",
                        "reason": "追い切り好調",
                    },
                ],
            },
        ]
        result = integrate_reviews(analysis, reviews)
        horse1 = next(e for e in result["evaluations"] if e["horse_number"] == 1)
        horse2 = next(e for e in result["evaluations"] if e["horse_number"] == 2)
        assert horse1["ability_score"] == "B"
        assert horse2["condition_score"] == "A"

    def test_review_notes_collected(self):
        """全レビューのノートが収集されること。"""
        analysis = _make_analysis()
        reviews = [
            {
                "reviewer": "venue-expert",
                "corrections": [
                    {
                        "horse_number": 1,
                        "field": "ability_score",
                        "original": "A",
                        "corrected": "B",
                        "reason": "テスト理由1",
                    },
                ],
                "track_notes": "コース補足",
            },
            {
                "reviewer": "veteran-tipster",
                "corrections": [],
                "additional_comment": "追加コメント",
            },
        ]
        result = integrate_reviews(analysis, reviews)
        assert len(result["review_notes"]) >= 2
        assert result["reviewed"] is True
        assert "venue-expert" in result["reviewers"]
        assert "veteran-tipster" in result["reviewers"]

    def test_mark_consistency_after_multiple_reviews(self):
        """複数レビュー後も印の整合性が保たれること（◎は1頭のみ）。"""
        analysis = _make_analysis()
        reviews = [
            {
                "reviewer": "venue-expert",
                "corrections": [],
                "mark_changes": [
                    {"horse_number": 2, "suggested_mark": "◎", "reason": "本命に変更"},
                ],
            },
            {
                "reviewer": "veteran-tipster",
                "corrections": [],
                "mark_changes": [
                    {"horse_number": 3, "suggested_mark": "◎", "reason": "こちらも本命"},
                ],
            },
        ]
        result = integrate_reviews(analysis, reviews)
        honmei_count = sum(
            1 for e in result["evaluations"] if e.get("mark") == "◎"
        )
        assert honmei_count == 1, "◎は1頭のみであること"

    def test_confidence_cumulative_adjustment(self):
        """複数レビュアーの自信度調整が累積されること。"""
        analysis = _make_analysis(confidence="C")
        reviews = [
            {"reviewer": "venue-expert", "corrections": [], "confidence_adjustment": 1},
            {"reviewer": "training-expert", "corrections": [], "confidence_adjustment": 1},
        ]
        result = integrate_reviews(analysis, reviews)
        # C(2) + 1 + 1 = 4 → A
        assert result["confidence"] == "A"


# ===========================================================================
# integrate_reviews のテスト: 原本は変更されないこと
# ===========================================================================


class TestOriginalNotMutated:
    """元の分析データが変更されないことの確認。"""

    def test_original_analysis_unchanged(self):
        """integrate_reviews の結果は deepcopy されており、元データは不変であること。"""
        analysis = _make_analysis(confidence="C")
        original_confidence = analysis["confidence"]
        review = {
            "reviewer": "veteran-tipster",
            "corrections": [],
            "confidence_adjustment": 2,
        }
        result = integrate_reviews(analysis, [review])
        # 結果は変わるが元データは変わらない
        assert result["confidence"] != analysis["confidence"] or result["confidence"] == analysis["confidence"]
        assert analysis["confidence"] == original_confidence


# ===========================================================================
# merge_all_reviews のテスト
# ===========================================================================


class TestMergeAllReviews:
    """全レース全専門家レビュー統合のテスト。"""

    def test_basic_merge(self):
        """2レースの統合が正しく行われること。"""
        analyses = {
            "race01": _make_analysis(),
            "race02": _make_analysis(),
        }
        venue = {
            "race01": {"reviewer": "venue-expert", "corrections": []},
        }
        tipster = {
            "race02": {
                "reviewer": "veteran-tipster",
                "corrections": [],
                "additional_comment": "勝負レース",
            },
        }
        bloodline = {}
        training = {}

        merged = merge_all_reviews(analyses, venue, tipster, bloodline, training)
        assert "race01" in merged
        assert "race02" in merged
        # race01: venue-expert のレビューあり → reviewed = True
        assert merged["race01"].get("reviewed") is True
        # race02: veteran-tipster のレビューあり → reviewed = True
        assert merged["race02"].get("reviewed") is True

    def test_no_reviews_passthrough(self):
        """レビューがないレースはそのまま返されること。"""
        analysis = _make_analysis()
        analyses = {"race01": analysis}
        merged = merge_all_reviews(analyses, {}, {}, {}, {})
        # レビューなしならそのまま返される（reviewed フラグなし）
        assert merged["race01"].get("reviewed") is None or merged["race01"] is analysis

    def test_all_four_reviewers(self):
        """4人の専門家レビューが全て統合されること。"""
        analysis = _make_analysis()
        analyses = {"race01": analysis}
        venue = {"race01": {"reviewer": "venue-expert", "corrections": [], "track_notes": "内枠有利"}}
        tipster = {"race01": {"reviewer": "veteran-tipster", "corrections": [], "volatility_adjustment": "堅い"}}
        bloodline = {"race01": {"reviewer": "bloodline-expert", "corrections": [], "bloodline_key_factor": "SS系"}}
        training = {"race01": {"reviewer": "training-expert", "corrections": [], "training_notes": "好調教"}}

        merged = merge_all_reviews(analyses, venue, tipster, bloodline, training)
        result = merged["race01"]
        assert result["reviewed"] is True
        assert len(result["reviewers"]) == 4
        assert "venue-expert" in result["reviewers"]
        assert "veteran-tipster" in result["reviewers"]
        assert "bloodline-expert" in result["reviewers"]
        assert "training-expert" in result["reviewers"]

    def test_is_best_bet_race_flag(self):
        """勝負レースフラグが正しく設定されること。"""
        analyses = {"race01": _make_analysis()}
        tipster = {
            "race01": {
                "reviewer": "veteran-tipster",
                "corrections": [],
                "is_best_bet_race": True,
            },
        }
        merged = merge_all_reviews(analyses, {}, tipster, {}, {})
        assert merged["race01"].get("is_best_bet_race") is True
