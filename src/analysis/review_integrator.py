"""
専門家レビューの統合モジュール。

4人の専門家（競馬場/予想家/血統/調教）のレビューを初期分析に反映し、
最終的な分析結果を生成する。
"""
from copy import deepcopy
from typing import Dict, List, Optional


# 評価グレードの数値変換（補正計算用）
GRADE_TO_NUM = {"A": 90, "B": 70, "C": 50, "D": 30, "E": 10}
NUM_TO_GRADE = [(80, "A"), (60, "B"), (40, "C"), (20, "D"), (0, "E")]

# 自信度の数値変換
CONFIDENCE_MAP = {"A": 4, "B": 3, "C": 2, "D": 1}
CONFIDENCE_REVERSE = {4: "A", 3: "B", 2: "C", 1: "D"}


def _num_to_grade(val: float) -> str:
    """数値をグレードに変換する。"""
    for threshold, grade in NUM_TO_GRADE:
        if val >= threshold:
            return grade
    return "E"


def integrate_reviews(
    original_analysis: dict,
    reviews: List[dict],
) -> dict:
    """
    初期分析に専門家レビューを統合して最終分析を生成する。

    Parameters
    ----------
    original_analysis : dict
        RaceAnalysis.to_dict() の出力
    reviews : list of dict
        各専門家のレビュー結果のリスト

    Returns
    -------
    dict
        レビューを反映した最終分析（同じフォーマット + review_notes 追加）
    """
    result = deepcopy(original_analysis)
    review_notes = []

    for review in reviews:
        reviewer = review.get("reviewer", "unknown")

        # --- 個別馬の評価補正 ---
        corrections = (
            review.get("corrections", [])
            + review.get("bloodline_corrections", [])
            + review.get("condition_corrections", [])
            + review.get("stable_corrections", [])
            + review.get("mark_changes", [])
        )

        for correction in corrections:
            horse_number = correction.get("horse_number")
            if horse_number is None:
                continue

            # 対象馬の評価を見つける
            for eval_data in result.get("evaluations", []):
                if eval_data.get("horse_number") != horse_number:
                    continue

                # フィールド名 → 評価キー名のマッピング
                field = correction.get("field", "")
                field_map = {
                    "ability_score": "ability_score",
                    "condition_score": "condition_score",
                    "jockey_score": "jockey_score",
                    "pace_score": "pace_score",
                    "bloodline_score": "bloodline_score",
                    "stable_score": "stable_score",
                }

                if field in field_map:
                    corrected = correction.get("corrected")
                    original = correction.get("original", eval_data.get(field_map[field]))
                    if corrected and corrected != original:
                        eval_data[field_map[field]] = corrected
                        reason = correction.get("reason", "")
                        review_notes.append(
                            f"[{reviewer}] {eval_data.get('horse_name', '')}({horse_number}番) "
                            f"{field}: {original}→{corrected} - {reason}"
                        )

                # 印の変更
                if "suggested_mark" in correction:
                    original_mark = correction.get("original_mark", eval_data.get("mark"))
                    suggested_mark = correction["suggested_mark"]
                    if suggested_mark != original_mark:
                        eval_data["mark"] = suggested_mark
                        reason = correction.get("reason", "")
                        review_notes.append(
                            f"[{reviewer}] {eval_data.get('horse_name', '')}({horse_number}番) "
                            f"印: {original_mark}→{suggested_mark} - {reason}"
                        )

                break  # 対象馬を見つけたらループ終了

        # --- 総合指数の再計算 ---
        _recalculate_indices(result)

        # --- コース傾向の補正（venue-expert） ---
        if reviewer == "venue-expert":
            if "track_notes" in review:
                result["track_condition_impact"] = (
                    result.get("track_condition_impact", "") + " " + review["track_notes"]
                ).strip()
                review_notes.append(f"[{reviewer}] コース補足: {review['track_notes']}")

        # --- 波乱度の補正（veteran-tipster） ---
        if reviewer == "veteran-tipster":
            vol_adj = review.get("volatility_adjustment")
            if vol_adj:
                old_vol = result.get("volatility", "")
                result["volatility"] = vol_adj
                review_notes.append(f"[{reviewer}] 波乱度: {old_vol}→{vol_adj}")

            # 追加コメント
            additional = review.get("additional_comment")
            if additional:
                result["comment"] = (
                    result.get("comment", "") + " / " + additional
                ).strip(" /")
                review_notes.append(f"[{reviewer}] 追加見解: {additional}")

            # 勝負レースフラグ
            if review.get("is_best_bet_race"):
                result["is_best_bet_race"] = True
                review_notes.append(f"[{reviewer}] 勝負レースに推薦")

        # --- 血統キーファクター（bloodline-expert） ---
        if reviewer == "bloodline-expert":
            key_factor = review.get("bloodline_key_factor")
            if key_factor:
                result["bloodline_key_factor"] = key_factor
                review_notes.append(f"[{reviewer}] 血統キーファクター: {key_factor}")

            # 特注ノート
            for note in review.get("special_notes", []):
                hn = note.get("horse_number")
                note_text = note.get("note", "")
                if hn and note_text:
                    # value_horsesに追加
                    if "value_horses" not in result:
                        result["value_horses"] = []
                    result["value_horses"].append({
                        "horse_number": hn,
                        "reason": f"[血統注目] {note_text}",
                    })
                    review_notes.append(f"[{reviewer}] {hn}番特注: {note_text}")

        # --- 調教ノート（training-expert） ---
        if reviewer == "training-expert":
            training_notes = review.get("training_notes")
            if training_notes:
                result["training_notes"] = training_notes
                review_notes.append(f"[{reviewer}] 調教注目: {training_notes}")

        # --- 自信度の調整 ---
        conf_adj = review.get("confidence_adjustment", 0)
        if conf_adj != 0:
            current_conf = result.get("confidence", "C")
            current_num = CONFIDENCE_MAP.get(current_conf, 2)
            new_num = max(1, min(4, current_num + conf_adj))
            new_conf = CONFIDENCE_REVERSE.get(new_num, "C")
            if new_conf != current_conf:
                result["confidence"] = new_conf
                review_notes.append(
                    f"[{reviewer}] 自信度: {current_conf}→{new_conf}"
                )

    # --- 最終印の整合性チェック ---
    _reconcile_marks(result)

    # レビューノートを追加
    result["review_notes"] = review_notes
    result["reviewed"] = True
    result["reviewers"] = [r.get("reviewer", "unknown") for r in reviews]

    return result


def _recalculate_indices(analysis: dict) -> None:
    """評価グレードから総合指数を再計算する。"""
    weights = {
        "ability_score": 0.30,
        "condition_score": 0.15,
        "jockey_score": 0.15,
        "pace_score": 0.15,
        "bloodline_score": 0.15,
        "stable_score": 0.10,
    }

    for eval_data in analysis.get("evaluations", []):
        total = 0.0
        for field, weight in weights.items():
            grade = eval_data.get(field, "C")
            total += GRADE_TO_NUM.get(grade, 50) * weight
        eval_data["total_index"] = round(total, 1)

    # 総合指数順にソート
    analysis["evaluations"] = sorted(
        analysis.get("evaluations", []),
        key=lambda e: e.get("total_index", 0),
        reverse=True,
    )


def _reconcile_marks(analysis: dict) -> None:
    """
    印の整合性を確認し、必要に応じて調整する。
    - ◎は1頭のみ
    - ○は1頭のみ
    - ▲は1頭のみ
    - △は最大3頭
    - ×は自由
    """
    evaluations = analysis.get("evaluations", [])
    if not evaluations:
        return

    # 印ごとのカウント
    mark_counts = {"◎": 0, "○": 0, "▲": 0, "△": 0, "×": 0}
    for e in evaluations:
        mark = e.get("mark", "")
        if mark in mark_counts:
            mark_counts[mark] += 1

    # ◎が複数ある場合、指数最高のみ◎にし残りを○に
    if mark_counts["◎"] > 1:
        found_first = False
        for e in evaluations:
            if e.get("mark") == "◎":
                if not found_first:
                    found_first = True
                else:
                    e["mark"] = "○"

    # ○が複数ある場合、指数最高のみ○にし残りを▲に
    o_count = sum(1 for e in evaluations if e.get("mark") == "○")
    if o_count > 1:
        found_first = False
        for e in evaluations:
            if e.get("mark") == "○":
                if not found_first:
                    found_first = True
                else:
                    e["mark"] = "▲"

    # honmei/taikou/tananaの更新
    analysis["honmei"] = next(
        (e for e in evaluations if e.get("mark") == "◎"), None
    )
    analysis["taikou"] = next(
        (e for e in evaluations if e.get("mark") == "○"), None
    )
    analysis["tanana"] = next(
        (e for e in evaluations if e.get("mark") == "▲"), None
    )
    analysis["renka"] = [e for e in evaluations if e.get("mark") == "△"]
    analysis["keshi"] = [e for e in evaluations if e.get("mark") == "×"]


def merge_all_reviews(
    analyses: Dict[str, dict],
    venue_reviews: Dict[str, dict],
    tipster_reviews: Dict[str, dict],
    bloodline_reviews: Dict[str, dict],
    training_reviews: Dict[str, dict],
) -> Dict[str, dict]:
    """
    全レースの全専門家レビューを統合する。

    Parameters
    ----------
    analyses : dict
        race_id -> analysis dict
    venue_reviews, tipster_reviews, bloodline_reviews, training_reviews : dict
        race_id -> review dict（各専門家）

    Returns
    -------
    dict
        race_id -> レビュー統合済み analysis dict
    """
    merged = {}
    for race_id, analysis in analyses.items():
        reviews = []
        if race_id in venue_reviews:
            reviews.append(venue_reviews[race_id])
        if race_id in tipster_reviews:
            reviews.append(tipster_reviews[race_id])
        if race_id in bloodline_reviews:
            reviews.append(bloodline_reviews[race_id])
        if race_id in training_reviews:
            reviews.append(training_reviews[race_id])

        if reviews:
            merged[race_id] = integrate_reviews(analysis, reviews)
        else:
            merged[race_id] = analysis

    return merged
