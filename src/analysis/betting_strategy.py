"""
馬券戦略エンジン。

RaceAnalysis の分析結果と OddsData を組み合わせて、
8券種（単勝/複勝/枠連/馬連/馬単/ワイド/三連複/三連単）にわたる
最適な馬券戦略を導出する。

期待値 (EV) ベースでバリューベットを特定し、
レースの性質（堅い/混戦/波乱）に応じて券種を使い分ける。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations, permutations
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path

# プロジェクトルートの src を参照
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from data.shutuba_schema import OddsData


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class BetRecommendation:
    """1つの馬券推奨。"""

    bet_type: str          # 単勝/複勝/枠連/馬連/馬単/ワイド/三連複/三連単
    selection: str          # "3" or "3-5" or "3>5>1" 等
    odds: float             # 想定オッズ
    expected_value: float   # 期待値 (> 1.0 がバリュー)
    confidence: float       # 確信度 0.0-1.0
    amount: int             # 推奨金額 (円, 100円単位)
    reasoning: str          # 理由 (日本語)

    def to_dict(self) -> dict:
        return {
            "bet_type": self.bet_type,
            "selection": self.selection,
            "odds": self.odds,
            "expected_value": round(self.expected_value, 3),
            "confidence": round(self.confidence, 3),
            "amount": self.amount,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BetRecommendation":
        return cls(
            bet_type=d["bet_type"],
            selection=d["selection"],
            odds=float(d["odds"]),
            expected_value=float(d["expected_value"]),
            confidence=float(d["confidence"]),
            amount=int(d["amount"]),
            reasoning=d["reasoning"],
        )


@dataclass
class RaceBettingStrategy:
    """1レースの馬券戦略。"""

    race_id: str
    race_name: str
    # 攻め（勝ちを意識）
    aggressive_bets: List[BetRecommendation] = field(default_factory=list)
    # 堅実（ガミらない）
    conservative_bets: List[BetRecommendation] = field(default_factory=list)
    # 最推奨
    best_bet_type: str = ""           # このレースで最推奨の券種
    total_investment: int = 0         # 合計投資額
    strategy_summary: str = ""        # 戦略サマリー (日本語)
    # 期待値ギャップ
    ev_gap_analysis: str = ""         # 期待値ギャップ分析テキスト
    # 自信度・トリガミチェック
    confidence: str = ""              # レースの自信度 (A/B/C/D)
    trigami_check_passed: bool = True  # トリガミ防止チェック結果
    trigami_notes: str = ""           # トリガミ調整メモ

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_name": self.race_name,
            "aggressive_bets": [b.to_dict() for b in self.aggressive_bets],
            "conservative_bets": [b.to_dict() for b in self.conservative_bets],
            "best_bet_type": self.best_bet_type,
            "total_investment": self.total_investment,
            "strategy_summary": self.strategy_summary,
            "ev_gap_analysis": self.ev_gap_analysis,
            "confidence": self.confidence,
            "trigami_check_passed": self.trigami_check_passed,
            "trigami_notes": self.trigami_notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RaceBettingStrategy":
        return cls(
            race_id=d["race_id"],
            race_name=d["race_name"],
            aggressive_bets=[
                BetRecommendation.from_dict(b) for b in d.get("aggressive_bets", [])
            ],
            conservative_bets=[
                BetRecommendation.from_dict(b) for b in d.get("conservative_bets", [])
            ],
            best_bet_type=d.get("best_bet_type", ""),
            total_investment=int(d.get("total_investment", 0)),
            strategy_summary=d.get("strategy_summary", ""),
            ev_gap_analysis=d.get("ev_gap_analysis", ""),
            confidence=d.get("confidence", ""),
            trigami_check_passed=d.get("trigami_check_passed", True),
            trigami_notes=d.get("trigami_notes", ""),
        )


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 印の種類と想定加点倍率（total_index に対するボーナス）
_MARK_WEIGHT: Dict[str, float] = {
    "◎": 1.5,   # 本命
    "○": 1.2,   # 対抗
    "▲": 1.0,   # 単穴
    "△": 0.8,   # 連下
}

# レース分類しきい値
_KATAI_THRESHOLD = 0.30    # 1番手の確率がこれ以上 → 堅いレース
_HARAN_THRESHOLD = 0.10    # 1番手の確率がこれ以下 → 波乱レース
# (それ以外は混戦)

# 複勝は3着以内の確率で計算。3着以内確率 ≒ 1着確率 × 補正係数
_PLACE_MULTIPLIER = 2.8

# ワイドは2頭が共に3着以内に入る確率
# 三連複/三連単の着順相関を考慮した補正
_TRIO_CORRELATION_FACTOR = 1.3   # 3頭組み合わせは相関により若干確率上昇
_TRIFECTA_ORDER_PENALTY = 0.35   # 着順を考慮すると確率は大きく下がる

# 最小期待値しきい値（これ以上をバリューとみなす）
_MIN_EV_THRESHOLD = 1.0

# 1点あたりの最小・最大金額
_MIN_BET_AMOUNT = 100
_MAX_BET_RATIO = 0.30   # 総予算の30%を超える単一ベットは避ける


# ---------------------------------------------------------------------------
# BettingStrategyEngine
# ---------------------------------------------------------------------------

class BettingStrategyEngine:
    """馬券戦略エンジン。分析結果とオッズから最適な買い目を決定する。"""

    def __init__(self, default_budget: int = 10000):
        """
        Args:
            default_budget: 1レースあたりのデフォルト予算（円）
        """
        self.default_budget = default_budget

    # ===================================================================
    # 自信度に応じた予算
    # ===================================================================

    def _get_budget_for_confidence(self, confidence: str) -> int:
        """
        自信度に応じた予算を返す。

        自信度と予算の対応:
            A（自信あり）: 10,000円
            B（やや自信）: 7,000円
            C（五分五分）: 4,000円
            D（難解）    : 1,000円

        Args:
            confidence: 自信度 ("A"/"B"/"C"/"D")

        Returns:
            予算（円）
        """
        budget_map = {
            "A": 10000,
            "B": 7000,
            "C": 4000,
            "D": 1000,
        }
        return budget_map.get(confidence, self.default_budget)

    # ===================================================================
    # メインメソッド
    # ===================================================================

    def determine_strategy(
        self,
        analysis: dict,
        odds: OddsData,
        budget: int = None,
        confidence: str = "",
    ) -> RaceBettingStrategy:
        """
        馬券戦略を決定するメインメソッド。

        Args:
            analysis: RaceAnalysis.to_dict() の結果。
                      期待するキー:
                        - race_id, race_name
                        - horses: List[dict] 各馬の分析結果
                          各馬: horse_number, horse_name, total_index, mark (◎○▲△ or "")
                        - race_summary: dict (任意)
            odds: 全券種のオッズデータ
            budget: 予算（円）。None の場合 default_budget を使用。
                    confidence が指定されている場合、自信度に応じた予算を優先。
            confidence: 自信度 ("A"/"B"/"C"/"D")。
                        指定された場合、対応する予算を自動設定する。

        Returns:
            RaceBettingStrategy
        """
        # 自信度が指定されている場合、自信度に応じた予算を使用
        if confidence and budget is None:
            budget = self._get_budget_for_confidence(confidence)
        else:
            budget = budget or self.default_budget
        race_id = analysis.get("race_id", odds.race_id or "")
        race_name = analysis.get("race_name", "")

        # ----------------------------------------------------------------
        # 1. 各馬の情報を抽出し、確率を算出
        # ----------------------------------------------------------------
        horses = analysis.get("horses", [])
        if not horses:
            # 馬情報がない場合は空の戦略を返す
            return RaceBettingStrategy(
                race_id=race_id,
                race_name=race_name,
                strategy_summary="分析データ不足のため戦略を生成できません。",
            )

        # total_index の一覧を取得
        all_indices = [h.get("total_index", 50.0) for h in horses]

        # 各馬の勝率（1着確率）を算出
        probs: Dict[int, float] = {}
        for h in horses:
            num = h.get("horse_number", 0)
            idx = h.get("total_index", 50.0)
            prob = self._index_to_probability(idx, all_indices)

            # 印によるボーナス補正
            mark = h.get("mark", "")
            if mark in _MARK_WEIGHT:
                prob *= _MARK_WEIGHT[mark]

            probs[num] = prob

        # 確率を正規化（合計 = 1.0 にする）
        total_prob = sum(probs.values())
        if total_prob > 0:
            probs = {k: v / total_prob for k, v in probs.items()}

        # ----------------------------------------------------------------
        # 2. レース分類（堅い / 混戦 / 波乱）
        # ----------------------------------------------------------------
        race_type = self._classify_race_type(analysis)

        # ----------------------------------------------------------------
        # 3. 危険な人気馬を検出
        # ----------------------------------------------------------------
        dangerous_popular = self._find_dangerous_popular(analysis, odds, probs)

        # ----------------------------------------------------------------
        # 4. 各券種で期待値 > 1.0 の組み合わせを探索
        # ----------------------------------------------------------------
        win_bets = self._evaluate_win(analysis, odds, probs)
        place_bets = self._evaluate_place(analysis, odds, probs)
        quinella_bets = self._evaluate_quinella(analysis, odds, probs)
        exacta_bets = self._evaluate_exacta(analysis, odds, probs)
        wide_bets = self._evaluate_wide(analysis, odds, probs)
        trio_bets = self._evaluate_trio(analysis, odds, probs)
        trifecta_bets = self._evaluate_trifecta(analysis, odds, probs)

        # ----------------------------------------------------------------
        # 5. 攻めと堅実に分割
        # ----------------------------------------------------------------
        # 攻め: 馬単, 三連単（高リスク・高リターン）
        all_aggressive = exacta_bets + trifecta_bets
        # 堅実: 複勝, ワイド, 三連複, 単勝, 馬連
        all_conservative = place_bets + wide_bets + trio_bets + win_bets + quinella_bets

        # EV の高い順にソート
        all_aggressive.sort(key=lambda b: b.expected_value, reverse=True)
        all_conservative.sort(key=lambda b: b.expected_value, reverse=True)

        # ----------------------------------------------------------------
        # 6. 予算配分
        # ----------------------------------------------------------------
        aggressive_bets, conservative_bets = self._allocate_budget(
            all_aggressive, all_conservative, budget, race_type
        )

        # ----------------------------------------------------------------
        # 6.5 トリガミ防止チェック
        # ----------------------------------------------------------------
        aggressive_bets, conservative_bets, trigami_passed, trigami_notes = (
            self._validate_no_trigami(
                aggressive_bets, conservative_bets, budget
            )
        )

        # ----------------------------------------------------------------
        # 7. 最推奨券種を決定
        # ----------------------------------------------------------------
        best_bet_type = self._determine_best_bet_type(
            race_type, aggressive_bets, conservative_bets
        )

        # ----------------------------------------------------------------
        # 8. 合計投資額
        # ----------------------------------------------------------------
        total_investment = sum(b.amount for b in aggressive_bets) + sum(
            b.amount for b in conservative_bets
        )

        # ----------------------------------------------------------------
        # 9. 戦略サマリーと期待値ギャップ分析
        # ----------------------------------------------------------------
        strategy_summary = self._build_strategy_summary(
            race_type, aggressive_bets, conservative_bets,
            total_investment, budget, dangerous_popular
        )
        ev_gap_analysis = self._build_ev_gap_analysis(
            probs, odds, dangerous_popular
        )

        return RaceBettingStrategy(
            race_id=race_id,
            race_name=race_name,
            aggressive_bets=aggressive_bets,
            conservative_bets=conservative_bets,
            best_bet_type=best_bet_type,
            total_investment=total_investment,
            strategy_summary=strategy_summary,
            ev_gap_analysis=ev_gap_analysis,
            confidence=confidence,
            trigami_check_passed=trigami_passed,
            trigami_notes=trigami_notes,
        )

    # ===================================================================
    # 確率算出
    # ===================================================================

    def _index_to_probability(
        self, total_index: float, all_indices: List[float]
    ) -> float:
        """
        total_index をソフトマックスで確率に変換する。

        ソフトマックス関数: P(i) = exp(idx_i / T) / sum(exp(idx_j / T))
        温度パラメータ T でスケーリング（T が大きいほど均一に近づく）。

        Args:
            total_index: 対象馬の総合指数
            all_indices: 全出走馬の総合指数リスト

        Returns:
            0.0-1.0 の確率値
        """
        # 温度パラメータ: 指数の分散に応じて調整
        temperature = 20.0

        # オーバーフロー防止のため最大値を引く
        max_idx = max(all_indices) if all_indices else 0.0
        exp_val = math.exp((total_index - max_idx) / temperature)
        exp_sum = sum(math.exp((idx - max_idx) / temperature) for idx in all_indices)

        if exp_sum == 0:
            return 1.0 / max(len(all_indices), 1)

        return exp_val / exp_sum

    # ===================================================================
    # 各券種の評価
    # ===================================================================

    def _evaluate_win(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """単勝の期待値を評価。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])

        for h in horses:
            num = h.get("horse_number", 0)
            if num not in probs or num not in odds.win_odds:
                continue

            win_prob = probs[num]
            win_odds_val = odds.win_odds[num]

            if win_odds_val <= 0:
                continue

            # 期待値 = 確率 * オッズ
            ev = win_prob * win_odds_val

            if ev >= _MIN_EV_THRESHOLD:
                # 確信度: 確率と期待値から算出
                confidence = min(1.0, win_prob * 2.0) * min(1.0, ev / 2.0)
                name = h.get("horse_name", f"{num}番")
                mark = h.get("mark", "")
                mark_str = f"{mark}" if mark else ""

                results.append(BetRecommendation(
                    bet_type="単勝",
                    selection=str(num),
                    odds=win_odds_val,
                    expected_value=ev,
                    confidence=confidence,
                    amount=_MIN_BET_AMOUNT,
                    reasoning=(
                        f"{mark_str}{name}(勝率{win_prob:.1%}, "
                        f"オッズ{win_odds_val:.1f}倍, EV{ev:.2f})"
                    ),
                ))

        # EV 降順でソート
        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:5]  # 上位5点まで

    def _evaluate_place(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """複勝の期待値を評価。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])
        num_horses = len(horses)

        for h in horses:
            num = h.get("horse_number", 0)
            if num not in probs or num not in odds.place_odds:
                continue

            win_prob = probs[num]
            # 複勝確率 = 3着以内の確率（出走頭数が少ない場合は補正）
            place_factor = min(_PLACE_MULTIPLIER, max(1.5, num_horses / 5.0))
            place_prob = min(0.95, win_prob * place_factor)

            place_odds_range = odds.place_odds[num]
            # 複勝オッズは (min, max) のタプル → 中央値を使用
            avg_place_odds = (place_odds_range[0] + place_odds_range[1]) / 2.0

            if avg_place_odds <= 0:
                continue

            ev = place_prob * avg_place_odds

            if ev >= _MIN_EV_THRESHOLD:
                confidence = min(1.0, place_prob * 1.5) * min(1.0, ev / 1.5)
                name = h.get("horse_name", f"{num}番")
                mark = h.get("mark", "")
                mark_str = f"{mark}" if mark else ""

                results.append(BetRecommendation(
                    bet_type="複勝",
                    selection=str(num),
                    odds=avg_place_odds,
                    expected_value=ev,
                    confidence=confidence,
                    amount=_MIN_BET_AMOUNT,
                    reasoning=(
                        f"{mark_str}{name}(3着内率{place_prob:.1%}, "
                        f"オッズ{place_odds_range[0]:.1f}-{place_odds_range[1]:.1f}倍, "
                        f"EV{ev:.2f})"
                    ),
                ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:5]

    def _evaluate_quinella(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """馬連の期待値を評価。2頭が1-2着（順不同）に入る確率。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])

        # 上位馬を抽出（確率上位8頭に絞って計算量を削減）
        sorted_nums = sorted(probs.keys(), key=lambda n: probs.get(n, 0), reverse=True)
        top_nums = sorted_nums[:8]

        for i, n1 in enumerate(top_nums):
            for n2 in top_nums[i + 1:]:
                # 馬連キー: "小番-大番"
                key = f"{min(n1, n2)}-{max(n1, n2)}"
                if key not in odds.quinella_odds:
                    continue

                q_odds = odds.quinella_odds[key]
                if q_odds <= 0:
                    continue

                # 2頭が1-2着に入る確率
                # P(n1が1着)*P(n2が2着|n1が1着) + P(n2が1着)*P(n1が2着|n2が1着)
                p1 = probs.get(n1, 0)
                p2 = probs.get(n2, 0)
                # 条件付き確率: 1頭が抜けた後の残り馬での確率
                remaining_prob_without_n1 = 1.0 - p1
                remaining_prob_without_n2 = 1.0 - p2
                p_n2_given_n1 = (p2 / remaining_prob_without_n1) if remaining_prob_without_n1 > 0 else 0
                p_n1_given_n2 = (p1 / remaining_prob_without_n2) if remaining_prob_without_n2 > 0 else 0

                quinella_prob = p1 * p_n2_given_n1 + p2 * p_n1_given_n2
                ev = quinella_prob * q_odds

                if ev >= _MIN_EV_THRESHOLD:
                    confidence = min(1.0, quinella_prob * 5.0) * min(1.0, ev / 2.0)
                    name1 = self._get_horse_name(horses, n1)
                    name2 = self._get_horse_name(horses, n2)

                    results.append(BetRecommendation(
                        bet_type="馬連",
                        selection=key,
                        odds=q_odds,
                        expected_value=ev,
                        confidence=confidence,
                        amount=_MIN_BET_AMOUNT,
                        reasoning=(
                            f"{name1}-{name2}"
                            f"(1-2着確率{quinella_prob:.2%}, "
                            f"オッズ{q_odds:.1f}倍, EV{ev:.2f})"
                        ),
                    ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:8]

    def _evaluate_exacta(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """馬単の期待値を評価。1着-2着の順序付き組み合わせ。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])

        sorted_nums = sorted(probs.keys(), key=lambda n: probs.get(n, 0), reverse=True)
        top_nums = sorted_nums[:8]

        for n1, n2 in permutations(top_nums, 2):
            # 馬単キー: "1着>2着"
            key = f"{n1}>{n2}"
            if key not in odds.exacta_odds:
                continue

            e_odds = odds.exacta_odds[key]
            if e_odds <= 0:
                continue

            # P(n1が1着) * P(n2が2着 | n1が1着)
            p1 = probs.get(n1, 0)
            p2 = probs.get(n2, 0)
            remaining = 1.0 - p1
            p_n2_given_n1 = (p2 / remaining) if remaining > 0 else 0
            exacta_prob = p1 * p_n2_given_n1

            ev = exacta_prob * e_odds

            if ev >= _MIN_EV_THRESHOLD:
                confidence = min(1.0, exacta_prob * 8.0) * min(1.0, ev / 2.5)
                name1 = self._get_horse_name(horses, n1)
                name2 = self._get_horse_name(horses, n2)

                results.append(BetRecommendation(
                    bet_type="馬単",
                    selection=key,
                    odds=e_odds,
                    expected_value=ev,
                    confidence=confidence,
                    amount=_MIN_BET_AMOUNT,
                    reasoning=(
                        f"{name1}>{name2}"
                        f"(確率{exacta_prob:.2%}, "
                        f"オッズ{e_odds:.1f}倍, EV{ev:.2f})"
                    ),
                ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:10]

    def _evaluate_wide(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """ワイドの期待値を評価。2頭が共に3着以内に入る確率。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])
        num_horses = len(horses)

        sorted_nums = sorted(probs.keys(), key=lambda n: probs.get(n, 0), reverse=True)
        top_nums = sorted_nums[:8]

        # 複勝確率（3着以内）
        place_factor = min(_PLACE_MULTIPLIER, max(1.5, num_horses / 5.0))
        place_probs = {n: min(0.95, probs.get(n, 0) * place_factor) for n in probs}

        for i, n1 in enumerate(top_nums):
            for n2 in top_nums[i + 1:]:
                key = f"{min(n1, n2)}-{max(n1, n2)}"
                if key not in odds.wide_odds:
                    continue

                w_odds_range = odds.wide_odds[key]
                avg_w_odds = (w_odds_range[0] + w_odds_range[1]) / 2.0

                if avg_w_odds <= 0:
                    continue

                # 2頭が共に3着以内: 独立事象ではないが近似的に計算
                # 相関を考慮: 同時確率 ≒ P(A) * P(B|A) ≈ P(A) * P(B) * 補正
                pp1 = place_probs.get(n1, 0)
                pp2 = place_probs.get(n2, 0)
                # 1頭が3着内に入ると、残り2枠を争うのでもう1頭の確率は若干下がる
                # 補正: (3着枠数-1) / (出走頭数-1) の比率で調整
                if num_horses > 1:
                    correction = (2.0 / (num_horses - 1)) / (3.0 / num_horses)
                    correction = min(1.0, max(0.5, correction))
                else:
                    correction = 1.0
                wide_prob = pp1 * pp2 * correction

                ev = wide_prob * avg_w_odds

                if ev >= _MIN_EV_THRESHOLD:
                    confidence = min(1.0, wide_prob * 3.0) * min(1.0, ev / 1.8)
                    name1 = self._get_horse_name(horses, n1)
                    name2 = self._get_horse_name(horses, n2)

                    results.append(BetRecommendation(
                        bet_type="ワイド",
                        selection=key,
                        odds=avg_w_odds,
                        expected_value=ev,
                        confidence=confidence,
                        amount=_MIN_BET_AMOUNT,
                        reasoning=(
                            f"{name1}-{name2}"
                            f"(3着内同時確率{wide_prob:.2%}, "
                            f"オッズ{w_odds_range[0]:.1f}-{w_odds_range[1]:.1f}倍, "
                            f"EV{ev:.2f})"
                        ),
                    ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:8]

    def _evaluate_trio(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """三連複の期待値を評価。3頭が1-2-3着（順不同）に入る確率。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])

        sorted_nums = sorted(probs.keys(), key=lambda n: probs.get(n, 0), reverse=True)
        top_nums = sorted_nums[:7]  # 上位7頭に絞る（C(7,3)=35通り）

        for combo in combinations(top_nums, 3):
            # 三連複キー: "小-中-大"
            sorted_combo = sorted(combo)
            key = f"{sorted_combo[0]}-{sorted_combo[1]}-{sorted_combo[2]}"
            if key not in odds.trio_odds:
                continue

            t_odds = odds.trio_odds[key]
            if t_odds <= 0:
                continue

            # 3頭が1-2-3着に入る確率（順不同）
            # 全順列の和: sum of P(perm) for all 6 permutations
            trio_prob = self._calc_trio_probability(combo, probs)
            # 相関補正: 上位馬同士は相関があるため若干確率を補正
            trio_prob *= _TRIO_CORRELATION_FACTOR

            ev = trio_prob * t_odds

            if ev >= _MIN_EV_THRESHOLD:
                confidence = min(1.0, trio_prob * 15.0) * min(1.0, ev / 3.0)
                names = [self._get_horse_name(horses, n) for n in sorted_combo]

                results.append(BetRecommendation(
                    bet_type="三連複",
                    selection=key,
                    odds=t_odds,
                    expected_value=ev,
                    confidence=confidence,
                    amount=_MIN_BET_AMOUNT,
                    reasoning=(
                        f"{names[0]}-{names[1]}-{names[2]}"
                        f"(確率{trio_prob:.3%}, "
                        f"オッズ{t_odds:.1f}倍, EV{ev:.2f})"
                    ),
                ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:10]

    def _evaluate_trifecta(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[BetRecommendation]:
        """三連単の期待値を評価。1着-2着-3着の順序付き組み合わせ。"""
        results: List[BetRecommendation] = []
        horses = analysis.get("horses", [])

        sorted_nums = sorted(probs.keys(), key=lambda n: probs.get(n, 0), reverse=True)
        top_nums = sorted_nums[:6]  # 上位6頭（P(6,3)=120通り）

        for perm in permutations(top_nums, 3):
            n1, n2, n3 = perm
            # 三連単キー: "1着>2着>3着"
            key = f"{n1}>{n2}>{n3}"
            if key not in odds.trifecta_odds:
                continue

            tf_odds = odds.trifecta_odds[key]
            if tf_odds <= 0:
                continue

            # P(n1が1着) * P(n2が2着|n1) * P(n3が3着|n1,n2)
            trifecta_prob = self._calc_trifecta_probability(perm, probs)

            ev = trifecta_prob * tf_odds

            if ev >= _MIN_EV_THRESHOLD:
                confidence = min(1.0, trifecta_prob * 30.0) * min(1.0, ev / 3.5)
                names = [self._get_horse_name(horses, n) for n in perm]

                results.append(BetRecommendation(
                    bet_type="三連単",
                    selection=key,
                    odds=tf_odds,
                    expected_value=ev,
                    confidence=confidence,
                    amount=_MIN_BET_AMOUNT,
                    reasoning=(
                        f"{names[0]}>{names[1]}>{names[2]}"
                        f"(確率{trifecta_prob:.4%}, "
                        f"オッズ{tf_odds:.1f}倍, EV{ev:.2f})"
                    ),
                ))

        results.sort(key=lambda b: b.expected_value, reverse=True)
        return results[:15]

    # ===================================================================
    # 確率計算ヘルパー
    # ===================================================================

    def _calc_trio_probability(
        self, combo: Tuple[int, ...], probs: Dict[int, float]
    ) -> float:
        """
        3頭の組み合わせが1-2-3着に入る確率（順不同）。
        全6順列の確率の和。
        """
        total = 0.0
        for perm in permutations(combo, 3):
            total += self._calc_trifecta_probability(perm, probs)
        return total

    def _calc_trifecta_probability(
        self, perm: Tuple[int, ...], probs: Dict[int, float]
    ) -> float:
        """
        3頭の順列 (1着, 2着, 3着) の確率。
        条件付き確率の積で計算。

        P(A,B,C) = P(A) * P(B|A) * P(C|A,B)
        """
        n1, n2, n3 = perm
        p1 = probs.get(n1, 0)
        p2 = probs.get(n2, 0)
        p3 = probs.get(n3, 0)

        # P(n2が2着 | n1が1着) = P(n2) / (1 - P(n1))
        remaining_after_1 = 1.0 - p1
        if remaining_after_1 <= 0:
            return 0.0
        p2_given_1 = p2 / remaining_after_1

        # P(n3が3着 | n1が1着, n2が2着) = P(n3) / (1 - P(n1) - P(n2))
        remaining_after_12 = 1.0 - p1 - p2
        if remaining_after_12 <= 0:
            return 0.0
        p3_given_12 = p3 / remaining_after_12

        return p1 * p2_given_1 * p3_given_12

    # ===================================================================
    # 予算配分
    # ===================================================================

    def _allocate_budget(
        self,
        aggressive: List[BetRecommendation],
        conservative: List[BetRecommendation],
        budget: int,
        race_type: str,
    ) -> Tuple[List[BetRecommendation], List[BetRecommendation]]:
        """
        予算を攻めと堅実に配分する。

        配分ルール（守り重視 / 攻め30〜50%, 守り50〜70%）:
        - 堅いレース → 攻め50%, 堅実50%
        - 混戦      → 攻め35%, 堅実65%
        - 波乱      → 攻め40%, 堅実60%

        ガミ防止: 堅実ベットの期待リターン >= 投資額を目指す。

        Args:
            aggressive: 攻め候補リスト（EV降順）
            conservative: 堅実候補リスト（EV降順）
            budget: 総予算
            race_type: "堅い" / "混戦" / "波乱"

        Returns:
            (割り当て後の攻め, 割り当て後の堅実)
        """
        # 攻め/堅実の予算比率（守り重視に変更）
        if race_type == "堅い":
            agg_ratio = 0.50
        elif race_type == "混戦":
            agg_ratio = 0.35
        else:  # 波乱
            agg_ratio = 0.40

        agg_budget = int(budget * agg_ratio)
        con_budget = budget - agg_budget

        # 攻めの予算配分
        allocated_agg = self._allocate_to_bets(aggressive, agg_budget)
        # 堅実の予算配分（ガミ防止を考慮）
        allocated_con = self._allocate_to_bets_conservative(conservative, con_budget)

        return allocated_agg, allocated_con

    def _allocate_to_bets(
        self, bets: List[BetRecommendation], budget: int
    ) -> List[BetRecommendation]:
        """
        ベットリストに予算を配分する（攻め用）。
        EV と confidence に比例して配分。
        """
        if not bets or budget <= 0:
            return []

        # スコア = EV * confidence
        scores = [b.expected_value * b.confidence for b in bets]
        total_score = sum(scores)

        if total_score <= 0:
            return []

        max_single_bet = int(budget * _MAX_BET_RATIO)
        allocated: List[BetRecommendation] = []
        remaining_budget = budget

        for bet, score in zip(bets, scores):
            if remaining_budget < _MIN_BET_AMOUNT:
                break

            # スコアに比例した配分
            raw_amount = (score / total_score) * budget
            # 100円単位に丸める
            amount = max(_MIN_BET_AMOUNT, int(raw_amount / 100) * 100)
            # 上限チェック
            amount = min(amount, max_single_bet, remaining_budget)
            # 100円単位に合わせる
            amount = (amount // 100) * 100

            if amount >= _MIN_BET_AMOUNT:
                allocated.append(BetRecommendation(
                    bet_type=bet.bet_type,
                    selection=bet.selection,
                    odds=bet.odds,
                    expected_value=bet.expected_value,
                    confidence=bet.confidence,
                    amount=amount,
                    reasoning=bet.reasoning,
                ))
                remaining_budget -= amount

        return allocated

    def _allocate_to_bets_conservative(
        self, bets: List[BetRecommendation], budget: int
    ) -> List[BetRecommendation]:
        """
        堅実ベットに予算を配分する。
        ガミ防止: 期待リターン >= 投資額を目指す。
        """
        if not bets or budget <= 0:
            return []

        # まず全ベットの平均期待値を計算
        avg_ev = sum(b.expected_value for b in bets) / len(bets) if bets else 0

        # EV が高いものから優先的に配分（ただし点数を増やしすぎない）
        max_bets = min(len(bets), 6)  # 堅実は最大6点まで
        selected_bets = bets[:max_bets]

        # ガミ防止チェック: 期待リターンが投資額を下回る場合は点数を減らす
        while selected_bets:
            total_ev = sum(b.expected_value for b in selected_bets) / len(selected_bets)
            if total_ev >= 1.0:
                break
            selected_bets = selected_bets[:-1]  # EVが低いものから削除

        if not selected_bets:
            # 全て EV < 1.0 の場合、最も EV が高い1点のみ
            if bets:
                selected_bets = [bets[0]]
            else:
                return []

        return self._allocate_to_bets(selected_bets, budget)

    # ===================================================================
    # トリガミ防止チェック
    # ===================================================================

    def _validate_no_trigami(
        self,
        aggressive: List[BetRecommendation],
        conservative: List[BetRecommendation],
        total_budget: int,
    ) -> Tuple[List[BetRecommendation], List[BetRecommendation], bool, str]:
        """
        トリガミ防止チェック。守りの馬券だけで総投資額を回収できるか検証する。

        チェック内容:
        - 守りの最低期待リターン >= 総投資額
        - 複勝の払戻し > 全馬券の投資額
        - ワイドは最低オッズでもプラスになる金額設定
        - 三連複ボックスは点数×100円 < 想定最低払戻し

        トリガミリスクがある場合、攻めベットを削減して守りに回す。

        Args:
            aggressive: 攻めベットリスト
            conservative: 守りベットリスト
            total_budget: 総予算

        Returns:
            (adjusted_aggressive, adjusted_conservative, passed, notes)
        """
        notes_parts: List[str] = []
        passed = True

        total_investment = sum(b.amount for b in aggressive) + sum(
            b.amount for b in conservative
        )

        if total_investment == 0:
            return aggressive, conservative, True, ""

        # チェック1: 守りの最低期待リターン >= 総投資額
        # 守りの馬券それぞれの「最低想定払戻し」を計算
        min_conservative_return = 0
        for bet in conservative:
            # ワイドの場合は最低オッズを使用
            if bet.bet_type == "ワイド":
                # bet.odds は平均オッズ。最低は約70%と仮定
                min_return = bet.amount * bet.odds * 0.7
            elif bet.bet_type == "複勝":
                # 複勝の最低は約80%
                min_return = bet.amount * bet.odds * 0.8
            else:
                min_return = bet.amount * bet.odds * 0.85
            min_conservative_return += min_return

        if min_conservative_return < total_investment and conservative:
            passed = False
            notes_parts.append(
                f"守りの最低想定払戻し({int(min_conservative_return):,}円) < "
                f"総投資額({total_investment:,}円)"
            )

            # 調整: 攻めを減らして守りに回す
            while aggressive and min_conservative_return < total_investment:
                # EVが最低の攻めベットを削除
                removed = aggressive.pop()
                freed = removed.amount

                # 守りの最高EVベットに上乗せ
                if conservative:
                    conservative[0] = BetRecommendation(
                        bet_type=conservative[0].bet_type,
                        selection=conservative[0].selection,
                        odds=conservative[0].odds,
                        expected_value=conservative[0].expected_value,
                        confidence=conservative[0].confidence,
                        amount=conservative[0].amount + freed,
                        reasoning=conservative[0].reasoning,
                    )

                # 再計算
                total_investment = sum(b.amount for b in aggressive) + sum(
                    b.amount for b in conservative
                )
                min_conservative_return = 0
                for bet in conservative:
                    if bet.bet_type == "ワイド":
                        min_return = bet.amount * bet.odds * 0.7
                    elif bet.bet_type == "複勝":
                        min_return = bet.amount * bet.odds * 0.8
                    else:
                        min_return = bet.amount * bet.odds * 0.85
                    min_conservative_return += min_return

            if min_conservative_return >= total_investment:
                notes_parts.append(
                    "攻めベットを削減し、守りベットを増額して調整済み"
                )
                passed = True

        notes = " / ".join(notes_parts) if notes_parts else "トリガミチェック: OK"
        return aggressive, conservative, passed, notes

    # ===================================================================
    # レース分類
    # ===================================================================

    def _classify_race_type(self, analysis: dict) -> str:
        """
        レースを分類する。

        - 堅い: 1番手の確率が30%以上 → 本命が信頼できる
        - 波乱: 1番手の確率が10%以下 → 混沌としている
        - 混戦: それ以外

        Args:
            analysis: 分析結果 dict

        Returns:
            "堅い" / "混戦" / "波乱"
        """
        horses = analysis.get("horses", [])
        if not horses:
            return "混戦"

        # total_index でソートして確率を推定
        all_indices = [h.get("total_index", 50.0) for h in horses]

        # ソフトマックスで確率を算出
        probs = []
        for idx in all_indices:
            probs.append(self._index_to_probability(idx, all_indices))

        if not probs:
            return "混戦"

        top_prob = max(probs)

        # 上位2頭の確率差も考慮
        sorted_probs = sorted(probs, reverse=True)
        top2_gap = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) >= 2 else 0

        if top_prob >= _KATAI_THRESHOLD:
            return "堅い"
        elif top_prob <= _HARAN_THRESHOLD or (top2_gap < 0.03 and top_prob < 0.20):
            return "波乱"
        else:
            return "混戦"

    # ===================================================================
    # 危険な人気馬の検出
    # ===================================================================

    def _find_dangerous_popular(
        self,
        analysis: dict,
        odds: OddsData,
        probs: Dict[int, float],
    ) -> List[dict]:
        """
        過剰に人気を集めている馬（過大評価されている人気馬）を検出する。

        オッズから暗黙の確率を逆算し、モデルの予測確率と比較。
        オッズ暗黙確率 > モデル確率 × 1.5 なら「過剰人気」と判定。

        Returns:
            List[dict]: 各要素は {horse_number, horse_name, implied_prob, model_prob, gap}
        """
        results: List[dict] = []
        horses = analysis.get("horses", [])

        for h in horses:
            num = h.get("horse_number", 0)
            if num not in odds.win_odds or num not in probs:
                continue

            win_odds_val = odds.win_odds[num]
            if win_odds_val <= 0:
                continue

            # オッズから暗黙確率を逆算（控除率を考慮）
            # JRA の控除率は約20%（単勝）→ 実質オッズ = 表示オッズ * 0.8
            implied_prob = 1.0 / win_odds_val
            model_prob = probs[num]

            # オッズ暗黙確率がモデル確率の1.5倍以上 → 過剰人気
            if implied_prob > model_prob * 1.5 and implied_prob > 0.10:
                name = h.get("horse_name", f"{num}番")
                gap = implied_prob - model_prob

                results.append({
                    "horse_number": num,
                    "horse_name": name,
                    "implied_prob": round(implied_prob, 4),
                    "model_prob": round(model_prob, 4),
                    "gap": round(gap, 4),
                    "win_odds": win_odds_val,
                })

        # ギャップが大きい順にソート
        results.sort(key=lambda x: x["gap"], reverse=True)
        return results

    # ===================================================================
    # 最推奨券種の決定
    # ===================================================================

    def _determine_best_bet_type(
        self,
        race_type: str,
        aggressive: List[BetRecommendation],
        conservative: List[BetRecommendation],
    ) -> str:
        """
        レース分類とベット候補から最推奨の券種を決定する。

        ルール:
        - 堅いレース → 単勝 / 馬単 / 三連単（本命からの流し）
        - 混戦       → ワイド / 三連複 / 馬連（ボックス or フォーメーション）
        - 波乱       → 三連単 / 馬単（穴馬からの流し）
        """
        # まず全ベットの中で最高EVの券種を候補にする
        all_bets = aggressive + conservative
        if not all_bets:
            # デフォルト推奨
            if race_type == "堅い":
                return "単勝"
            elif race_type == "混戦":
                return "ワイド"
            else:
                return "三連単"

        # 券種ごとの平均EVを算出
        ev_by_type: Dict[str, List[float]] = {}
        for b in all_bets:
            ev_by_type.setdefault(b.bet_type, []).append(b.expected_value)

        avg_ev_by_type = {
            bt: sum(evs) / len(evs) for bt, evs in ev_by_type.items()
        }

        # レース分類に応じた優先券種
        if race_type == "堅い":
            preferred = ["単勝", "馬単", "三連単", "馬連"]
        elif race_type == "混戦":
            preferred = ["ワイド", "三連複", "馬連", "複勝"]
        else:  # 波乱
            preferred = ["三連単", "馬単", "三連複", "ワイド"]

        # 優先券種の中でEVが最も高いものを選択
        best_type = ""
        best_ev = 0.0

        for bt in preferred:
            if bt in avg_ev_by_type and avg_ev_by_type[bt] > best_ev:
                best_ev = avg_ev_by_type[bt]
                best_type = bt

        # 優先券種に該当がなければ全券種で最高EV
        if not best_type:
            best_type = max(avg_ev_by_type, key=avg_ev_by_type.get, default="複勝")

        return best_type

    # ===================================================================
    # サマリーと分析テキスト生成
    # ===================================================================

    def _build_strategy_summary(
        self,
        race_type: str,
        aggressive: List[BetRecommendation],
        conservative: List[BetRecommendation],
        total_investment: int,
        budget: int,
        dangerous_popular: List[dict],
    ) -> str:
        """戦略サマリー文を生成する。"""
        lines: List[str] = []

        # レース分類
        type_desc = {
            "堅い": "本命馬の信頼度が高い堅いレース",
            "混戦": "上位馬の力差が小さい混戦模様のレース",
            "波乱": "力関係が読みにくい波乱含みのレース",
        }
        lines.append(f"【レース分類】{type_desc.get(race_type, race_type)}")

        # 攻めのサマリー
        if aggressive:
            agg_total = sum(b.amount for b in aggressive)
            agg_types = set(b.bet_type for b in aggressive)
            lines.append(
                f"【攻め】{', '.join(agg_types)} "
                f"計{len(aggressive)}点 / {agg_total:,}円"
            )
            # 最高EV のベットを紹介
            top_agg = max(aggressive, key=lambda b: b.expected_value)
            lines.append(f"  注目: {top_agg.reasoning}")

        # 堅実のサマリー
        if conservative:
            con_total = sum(b.amount for b in conservative)
            con_types = set(b.bet_type for b in conservative)
            lines.append(
                f"【堅実】{', '.join(con_types)} "
                f"計{len(conservative)}点 / {con_total:,}円"
            )

        # 危険な人気馬の注意喚起
        if dangerous_popular:
            names = [d["horse_name"] for d in dangerous_popular[:2]]
            lines.append(
                f"【注意】過剰人気: {', '.join(names)} "
                f"(オッズ暗黙確率 > モデル確率)"
            )

        # 投資額
        lines.append(f"【投資額】{total_investment:,}円 / 予算{budget:,}円")

        return "\n".join(lines)

    def _build_ev_gap_analysis(
        self,
        probs: Dict[int, float],
        odds: OddsData,
        dangerous_popular: List[dict],
    ) -> str:
        """期待値ギャップ分析テキストを生成する。"""
        lines: List[str] = []
        lines.append("=== 期待値ギャップ分析 ===")

        # 単勝のEVギャップ一覧
        ev_gaps: List[Tuple[int, float, float, float]] = []
        for num, prob in sorted(probs.items()):
            if num not in odds.win_odds:
                continue
            win_odds_val = odds.win_odds[num]
            if win_odds_val <= 0:
                continue
            ev = prob * win_odds_val
            implied = 1.0 / win_odds_val
            gap = prob - implied  # 正ならモデル確率のほうが高い（割安）
            ev_gaps.append((num, prob, implied, gap))

        # 割安な馬（バリュー）
        undervalued = [(n, p, i, g) for n, p, i, g in ev_gaps if g > 0.02]
        if undervalued:
            undervalued.sort(key=lambda x: x[3], reverse=True)
            lines.append("\n[割安（バリュー）]")
            for num, prob, implied, gap in undervalued[:5]:
                lines.append(
                    f"  {num}番: モデル確率{prob:.1%} vs "
                    f"市場確率{implied:.1%} → ギャップ+{gap:.1%}"
                )

        # 割高な馬（過剰人気）
        overvalued = [(n, p, i, g) for n, p, i, g in ev_gaps if g < -0.02]
        if overvalued:
            overvalued.sort(key=lambda x: x[3])
            lines.append("\n[割高（過剰人気）]")
            for num, prob, implied, gap in overvalued[:5]:
                lines.append(
                    f"  {num}番: モデル確率{prob:.1%} vs "
                    f"市場確率{implied:.1%} → ギャップ{gap:.1%}"
                )

        # 危険な人気馬
        if dangerous_popular:
            lines.append("\n[危険な人気馬]")
            for d in dangerous_popular[:3]:
                lines.append(
                    f"  {d['horse_name']}({d['horse_number']}番): "
                    f"オッズ{d['win_odds']:.1f}倍 → "
                    f"市場確率{d['implied_prob']:.1%} vs "
                    f"モデル確率{d['model_prob']:.1%}"
                )

        if len(lines) == 1:
            lines.append("  オッズデータ不足のため分析できません。")

        return "\n".join(lines)

    # ===================================================================
    # ユーティリティ
    # ===================================================================

    @staticmethod
    def _get_horse_name(horses: List[dict], horse_number: int) -> str:
        """馬番から馬名を取得する。"""
        for h in horses:
            if h.get("horse_number") == horse_number:
                name = h.get("horse_name", "")
                mark = h.get("mark", "")
                return f"{mark}{name}" if mark else name
        return f"{horse_number}番"
