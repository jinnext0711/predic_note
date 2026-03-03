"""forward_record.py のテスト（フォワード成績モデル）。"""
import pytest

from models.forward_record import ForwardResult, ForwardRecord


class TestForwardResult:
    def test_profit_hit(self):
        """的中時の損益計算。"""
        result = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name="東京5R",
            bet_type="単勝", horse_name="テスト馬", horse_number=1,
            bet_amount=100, is_hit=True, payout=500.0,
        )
        assert result.profit() == 400.0

    def test_profit_miss(self):
        """不的中時の損益計算。"""
        result = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name="東京5R",
            bet_type="単勝", horse_name="テスト馬", horse_number=1,
            bet_amount=100, is_hit=False, payout=0.0,
        )
        assert result.profit() == -100.0

    def test_to_dict_and_from_dict(self):
        original = ForwardResult(
            race_id="R001", race_date="2024-06-01", race_name="東京5R",
            bet_type="複勝", horse_name="テスト馬", horse_number=3,
            bet_amount=200, is_hit=True, payout=400.0,
        )
        d = original.to_dict()
        restored = ForwardResult.from_dict(d)
        assert restored.race_id == "R001"
        assert restored.bet_type == "複勝"
        assert restored.horse_number == 3
        assert restored.bet_amount == 200
        assert restored.payout == 400.0


class TestForwardRecord:
    def _make_results(self):
        return [
            ForwardResult(
                race_id="R001", race_date="2024-06-01", race_name="東京5R",
                bet_type="単勝", horse_name="馬A", horse_number=1,
                bet_amount=100, is_hit=True, payout=500.0,
            ),
            ForwardResult(
                race_id="R002", race_date="2024-06-02", race_name="東京6R",
                bet_type="単勝", horse_name="馬B", horse_number=2,
                bet_amount=100, is_hit=False, payout=0.0,
            ),
            ForwardResult(
                race_id="R003", race_date="2024-06-03", race_name="東京7R",
                bet_type="単勝", horse_name="馬C", horse_number=3,
                bet_amount=100, is_hit=True, payout=300.0,
            ),
        ]

    def test_total_trials(self):
        record = ForwardRecord(logic_name="テスト", results=self._make_results())
        assert record.total_trials() == 3

    def test_total_hits(self):
        record = ForwardRecord(logic_name="テスト", results=self._make_results())
        assert record.total_hits() == 2

    def test_hit_rate(self):
        record = ForwardRecord(logic_name="テスト", results=self._make_results())
        assert round(record.hit_rate(), 1) == 66.7

    def test_recovery_rate(self):
        """回収率: (500 + 0 + 300) / (100 + 100 + 100) * 100 = 266.7%"""
        record = ForwardRecord(logic_name="テスト", results=self._make_results())
        assert round(record.recovery_rate(), 1) == 266.7

    def test_total_profit(self):
        """総損益: 800 - 300 = 500"""
        record = ForwardRecord(logic_name="テスト", results=self._make_results())
        assert record.total_profit() == 500.0

    def test_empty_record(self):
        record = ForwardRecord(logic_name="空テスト")
        assert record.total_trials() == 0
        assert record.hit_rate() == 0.0
        assert record.recovery_rate() == 0.0
        assert record.total_profit() == 0.0

    def test_to_dict_and_from_dict(self):
        original = ForwardRecord(logic_name="テスト", results=self._make_results())
        d = original.to_dict()
        restored = ForwardRecord.from_dict(d)
        assert restored.logic_name == "テスト"
        assert len(restored.results) == 3
        assert restored.total_hits() == 2
