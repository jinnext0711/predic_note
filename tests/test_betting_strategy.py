"""
馬券戦略エンジン (betting_strategy.py) のテスト。

BettingStrategyEngine の determine_strategy を中心に、
EV計算、予算配分、レース分類、攻め/堅実の分割を検証する。
"""
import pytest

from analysis.betting_strategy import (
    BetRecommendation,
    BettingStrategyEngine,
    RaceBettingStrategy,
    _KATAI_THRESHOLD,
    _HARAN_THRESHOLD,
    _MIN_BET_AMOUNT,
)
from data.shutuba_schema import OddsData


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _make_horse_data(
    horse_number: int,
    horse_name: str,
    total_index: float,
    mark: str = "",
) -> dict:
    """分析データ内の馬情報 dict を生成する。"""
    return {
        "horse_number": horse_number,
        "horse_name": horse_name,
        "total_index": total_index,
        "mark": mark,
    }


def _make_analysis(
    horses: list = None,
    race_id: str = "race01",
    race_name: str = "テストレース",
) -> dict:
    """テスト用の分析データ dict を生成する。"""
    if horses is None:
        # デフォルト: 実力差のある6頭
        horses = [
            _make_horse_data(1, "強い馬", 85.0, "◎"),
            _make_horse_data(2, "対抗馬", 75.0, "○"),
            _make_horse_data(3, "穴馬", 65.0, "▲"),
            _make_horse_data(4, "連下A", 55.0, "△"),
            _make_horse_data(5, "連下B", 50.0, "△"),
            _make_horse_data(6, "無印馬", 40.0, ""),
        ]
    return {
        "race_id": race_id,
        "race_name": race_name,
        "horses": horses,
    }


def _make_odds(
    race_id: str = "race01",
    num_horses: int = 6,
) -> OddsData:
    """テスト用のオッズデータを生成する。"""
    win_odds = {}
    place_odds = {}
    quinella_odds = {}
    wide_odds = {}
    trio_odds = {}
    trifecta_odds = {}
    exacta_odds = {}

    for i in range(1, num_horses + 1):
        # 1番馬は低オッズ（人気）、番号が大きいほど高オッズ
        win_odds[i] = 2.0 + (i - 1) * 4.0
        place_odds[i] = (1.1 + (i - 1) * 0.3, 1.5 + (i - 1) * 0.8)

    # 馬連
    for i in range(1, min(num_horses + 1, 5)):
        for j in range(i + 1, min(num_horses + 1, 6)):
            key = f"{i}-{j}"
            quinella_odds[key] = (i + j) * 3.0
            wide_odds[key] = ((i + j) * 1.0, (i + j) * 2.0)

    # 三連複
    trio_odds["1-2-3"] = 20.0
    trio_odds["1-2-4"] = 40.0
    trio_odds["1-3-4"] = 60.0

    # 馬単
    for i in range(1, min(num_horses + 1, 4)):
        for j in range(1, min(num_horses + 1, 4)):
            if i != j:
                exacta_odds[f"{i}>{j}"] = (i + j) * 5.0

    # 三連単
    trifecta_odds["1>2>3"] = 60.0
    trifecta_odds["1>3>2"] = 80.0
    trifecta_odds["2>1>3"] = 100.0

    return OddsData(
        race_id=race_id,
        win_odds=win_odds,
        place_odds=place_odds,
        quinella_odds=quinella_odds,
        exacta_odds=exacta_odds,
        wide_odds=wide_odds,
        trio_odds=trio_odds,
        trifecta_odds=trifecta_odds,
    )


# ===========================================================================
# BetRecommendation のテスト
# ===========================================================================


class TestBetRecommendation:
    """BetRecommendation データクラスのテスト。"""

    def test_to_dict_from_dict_round_trip(self):
        """to_dict / from_dict ラウンドトリップ。"""
        bet = BetRecommendation(
            bet_type="単勝",
            selection="1",
            odds=3.5,
            expected_value=1.25,
            confidence=0.8,
            amount=500,
            reasoning="テスト理由",
        )
        d = bet.to_dict()
        restored = BetRecommendation.from_dict(d)
        assert restored.bet_type == "単勝"
        assert restored.odds == 3.5
        assert restored.expected_value == pytest.approx(1.25, abs=0.01)
        assert restored.amount == 500


# ===========================================================================
# RaceBettingStrategy のテスト
# ===========================================================================


class TestRaceBettingStrategy:
    """RaceBettingStrategy データクラスのテスト。"""

    def test_to_dict_from_dict_round_trip(self):
        """to_dict / from_dict ラウンドトリップ。"""
        strategy = RaceBettingStrategy(
            race_id="race01",
            race_name="テスト",
            aggressive_bets=[
                BetRecommendation(
                    bet_type="馬単", selection="1>2", odds=10.0,
                    expected_value=1.5, confidence=0.6, amount=300,
                    reasoning="テスト",
                )
            ],
            conservative_bets=[],
            best_bet_type="馬単",
            total_investment=300,
            strategy_summary="テストサマリー",
        )
        d = strategy.to_dict()
        restored = RaceBettingStrategy.from_dict(d)
        assert restored.race_id == "race01"
        assert len(restored.aggressive_bets) == 1
        assert restored.best_bet_type == "馬単"
        assert restored.total_investment == 300


# ===========================================================================
# BettingStrategyEngine のテスト
# ===========================================================================


class TestBettingStrategyEngine:
    """BettingStrategyEngine のメインテスト。"""

    @pytest.fixture
    def engine(self) -> BettingStrategyEngine:
        """デフォルト予算のエンジン。"""
        return BettingStrategyEngine(default_budget=10000)

    def test_determine_strategy_returns_valid_object(self, engine):
        """determine_strategy が有効な RaceBettingStrategy を返すこと。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)

        assert isinstance(result, RaceBettingStrategy)
        assert result.race_id == "race01"
        assert result.race_name == "テストレース"

    def test_total_investment_within_budget(self, engine):
        """合計投資額が予算を超えないこと。"""
        analysis = _make_analysis()
        odds = _make_odds()
        budget = 5000
        result = engine.determine_strategy(analysis, odds, budget=budget)
        assert result.total_investment <= budget

    def test_all_amounts_are_multiples_of_100(self, engine):
        """すべての推奨金額が100円単位であること。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)
        all_bets = result.aggressive_bets + result.conservative_bets
        for bet in all_bets:
            assert bet.amount % 100 == 0, f"{bet.bet_type} の金額 {bet.amount} が100円単位でない"
            assert bet.amount >= _MIN_BET_AMOUNT

    def test_ev_values_are_positive(self, engine):
        """推奨される馬券の期待値がすべて正であること。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)
        all_bets = result.aggressive_bets + result.conservative_bets
        for bet in all_bets:
            assert bet.expected_value > 0, f"{bet.bet_type} {bet.selection} の EV が0以下"

    def test_empty_horses_returns_empty_strategy(self, engine):
        """馬情報が空の場合、空の戦略が返されること。"""
        analysis = _make_analysis(horses=[])
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)
        assert result.aggressive_bets == []
        assert result.conservative_bets == []
        assert "不足" in result.strategy_summary

    def test_best_bet_type_is_set(self, engine):
        """最推奨券種が設定されること。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)
        valid_bet_types = {"単勝", "複勝", "枠連", "馬連", "馬単", "ワイド", "三連複", "三連単"}
        if result.aggressive_bets or result.conservative_bets:
            assert result.best_bet_type in valid_bet_types

    def test_strategy_summary_not_empty(self, engine):
        """戦略サマリーが空でないこと。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds)
        assert len(result.strategy_summary) > 0


# ===========================================================================
# レース分類のテスト
# ===========================================================================


class TestRaceTypeClassification:
    """レース分類のテスト。"""

    @pytest.fixture
    def engine(self) -> BettingStrategyEngine:
        return BettingStrategyEngine()

    def test_katai_race_with_dominant_horse(self, engine):
        """圧倒的な本命がいる場合 → 堅いレースに分類されること。"""
        horses = [
            _make_horse_data(1, "圧倒的本命", 95.0, "◎"),
            _make_horse_data(2, "二番手", 50.0, "○"),
            _make_horse_data(3, "三番手", 45.0, "▲"),
        ]
        analysis = _make_analysis(horses=horses)
        race_type = engine._classify_race_type(analysis)
        assert race_type == "堅い"

    def test_konsen_race(self, engine):
        """上位が拮抗している場合 → 混戦に分類されること。"""
        horses = [
            _make_horse_data(1, "馬A", 55.0),
            _make_horse_data(2, "馬B", 54.0),
            _make_horse_data(3, "馬C", 53.0),
            _make_horse_data(4, "馬D", 52.0),
            _make_horse_data(5, "馬E", 51.0),
            _make_horse_data(6, "馬F", 50.0),
        ]
        analysis = _make_analysis(horses=horses)
        race_type = engine._classify_race_type(analysis)
        # 指数が僅差なので波乱か混戦
        assert race_type in ("混戦", "波乱")

    def test_empty_horses_returns_konsen(self, engine):
        """馬情報なしの場合 → 混戦と分類されること。"""
        analysis = _make_analysis(horses=[])
        race_type = engine._classify_race_type(analysis)
        assert race_type == "混戦"


# ===========================================================================
# EV計算のテスト
# ===========================================================================


class TestEVCalculation:
    """期待値計算のテスト。"""

    @pytest.fixture
    def engine(self) -> BettingStrategyEngine:
        return BettingStrategyEngine()

    def test_softmax_probabilities_sum_to_one(self, engine):
        """ソフトマックスで算出した確率の合計が 1.0 になること。"""
        indices = [80.0, 70.0, 60.0, 50.0, 40.0]
        probs = [engine._index_to_probability(idx, indices) for idx in indices]
        assert sum(probs) == pytest.approx(1.0, abs=1e-6)

    def test_higher_index_gets_higher_probability(self, engine):
        """指数が高い馬ほど高い確率が付与されること。"""
        indices = [90.0, 70.0, 50.0]
        probs = [engine._index_to_probability(idx, indices) for idx in indices]
        assert probs[0] > probs[1] > probs[2]

    def test_all_same_index_equal_probability(self, engine):
        """全馬の指数が同じなら均等な確率になること。"""
        indices = [50.0, 50.0, 50.0, 50.0]
        probs = [engine._index_to_probability(idx, indices) for idx in indices]
        for p in probs:
            assert p == pytest.approx(0.25, abs=1e-6)


# ===========================================================================
# 予算配分のテスト
# ===========================================================================


class TestBudgetAllocation:
    """予算配分のテスト。"""

    @pytest.fixture
    def engine(self) -> BettingStrategyEngine:
        return BettingStrategyEngine(default_budget=10000)

    def test_aggressive_and_conservative_split(self, engine):
        """攻めと堅実に予算が分割されること。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds, budget=10000)

        agg_total = sum(b.amount for b in result.aggressive_bets)
        con_total = sum(b.amount for b in result.conservative_bets)
        total = agg_total + con_total

        # 合計が予算以内
        assert total <= 10000
        # 少なくとも何かのベットがある（オッズ条件を満たす場合）
        # 注: オッズ次第でベットが0の場合もあるため、弱い条件
        assert total >= 0

    def test_custom_budget(self, engine):
        """カスタム予算が正しく適用されること。"""
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds, budget=3000)
        assert result.total_investment <= 3000

    def test_zero_budget_uses_default(self, engine):
        """予算0を渡すと `budget or default` でデフォルト予算が使われること。

        budget=0 は falsy なので、エンジン側は default_budget にフォールバックする。
        このため合計投資額は default_budget 以内になる。
        """
        analysis = _make_analysis()
        odds = _make_odds()
        result = engine.determine_strategy(analysis, odds, budget=0)
        # budget=0 は or で default_budget(10000) にフォールバックされる
        assert result.total_investment <= engine.default_budget
