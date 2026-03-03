"""MustLogic / MustBlock モデルのテスト。"""
import pytest
from models.must import MustBlock, MustLogic


class TestMustBlock:
    def test_valid_block(self):
        block = MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}])
        assert block.is_valid()

    def test_empty_block_invalid(self):
        block = MustBlock(conditions=[])
        assert not block.is_valid()

    def test_to_dict_and_from_dict(self):
        block = MustBlock(conditions=[
            {"category": "前走着順", "operator": "le", "value": "3"},
        ])
        d = block.to_dict()
        restored = MustBlock.from_dict(d)
        assert len(restored.conditions) == 1
        assert restored.conditions[0]["category"] == "前走着順"


class TestMustLogic:
    def test_valid_logic(self):
        logic = MustLogic(blocks=[
            MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}]),
        ])
        assert logic.is_valid()

    def test_to_dict_and_from_dict(self):
        logic = MustLogic(blocks=[
            MustBlock(conditions=[{"category": "斤量", "operator": "le", "value": "57"}]),
            MustBlock(conditions=[{"category": "前走着順", "operator": "le", "value": "3"}]),
        ])
        d = logic.to_dict()
        restored = MustLogic.from_dict(d)
        assert len(restored.blocks) == 2
        assert restored.blocks[0].conditions[0]["value"] == "57"

    def test_from_dict_empty(self):
        logic = MustLogic.from_dict({})
        assert len(logic.blocks) == 0
