"""auth_store.py のテスト（ユーザー認証・プラン管理）。"""
import pytest

from auth_store import (
    register_user,
    authenticate_user,
    is_paid_user,
    can_run_backtest,
    get_backtest_count,
    increment_backtest_count,
    FREE_BACKTEST_LIMIT,
)


# ── ユーザー登録 ──

class TestRegisterUser:
    def test_register_success(self, tmp_path):
        ok, msg = register_user("testuser", "password123", base_path=tmp_path)
        assert ok is True
        assert "完了" in msg

    def test_register_short_username(self, tmp_path):
        ok, msg = register_user("ab", "password123", base_path=tmp_path)
        assert ok is False
        assert "3文字" in msg

    def test_register_empty_username(self, tmp_path):
        ok, msg = register_user("", "password123", base_path=tmp_path)
        assert ok is False

    def test_register_short_password(self, tmp_path):
        ok, msg = register_user("testuser", "12345", base_path=tmp_path)
        assert ok is False
        assert "6文字" in msg

    def test_register_duplicate(self, tmp_path):
        register_user("testuser", "password123", base_path=tmp_path)
        ok, msg = register_user("testuser", "password456", base_path=tmp_path)
        assert ok is False
        assert "既に使用" in msg

    def test_register_whitespace_username(self, tmp_path):
        ok, msg = register_user("  test  ", "password123", base_path=tmp_path)
        assert ok is True
        # strip されたユーザー名でログインできる
        ok2, _ = authenticate_user("test", "password123", base_path=tmp_path)
        assert ok2 is True


# ── ログイン認証 ──

class TestAuthenticate:
    def test_login_success(self, tmp_path):
        register_user("testuser", "password123", base_path=tmp_path)
        ok, msg = authenticate_user("testuser", "password123", base_path=tmp_path)
        assert ok is True

    def test_login_wrong_password(self, tmp_path):
        register_user("testuser", "password123", base_path=tmp_path)
        ok, msg = authenticate_user("testuser", "wrongpass", base_path=tmp_path)
        assert ok is False

    def test_login_nonexistent_user(self, tmp_path):
        ok, msg = authenticate_user("nobody", "password", base_path=tmp_path)
        assert ok is False

    def test_login_empty_fields(self, tmp_path):
        ok, msg = authenticate_user("", "", base_path=tmp_path)
        assert ok is False


# ── プラン・バックテスト制限 ──

class TestPlanAndLimits:
    def test_new_user_is_free(self, tmp_path):
        register_user("freeuser", "password123", base_path=tmp_path)
        assert is_paid_user("freeuser", base_path=tmp_path) is False

    def test_free_user_cannot_backtest_own(self, tmp_path):
        """無料ユーザーは自分のロジックのバックテストを実行できない。"""
        register_user("freeuser", "password123", base_path=tmp_path)
        can_run, msg = can_run_backtest("freeuser", is_own_logic=True, base_path=tmp_path)
        assert can_run is False
        assert "有料プラン" in msg

    def test_free_user_can_backtest_others(self, tmp_path):
        """無料ユーザーは他人の公開ロジックを回数制限内で実行できる。"""
        register_user("freeuser", "password123", base_path=tmp_path)
        can_run, msg = can_run_backtest("freeuser", is_own_logic=False, base_path=tmp_path)
        assert can_run is True
        assert "残り" in msg

    def test_free_user_backtest_limit(self, tmp_path):
        """無料ユーザーのバックテスト回数制限。"""
        register_user("freeuser", "password123", base_path=tmp_path)
        for _ in range(FREE_BACKTEST_LIMIT):
            increment_backtest_count("freeuser", base_path=tmp_path)

        can_run, msg = can_run_backtest("freeuser", is_own_logic=False, base_path=tmp_path)
        assert can_run is False
        assert "制限" in msg

    def test_increment_backtest_count(self, tmp_path):
        register_user("counter", "password123", base_path=tmp_path)
        assert get_backtest_count("counter", base_path=tmp_path) == 0
        increment_backtest_count("counter", base_path=tmp_path)
        assert get_backtest_count("counter", base_path=tmp_path) == 1
        increment_backtest_count("counter", base_path=tmp_path)
        assert get_backtest_count("counter", base_path=tmp_path) == 2

    def test_nonexistent_user_not_paid(self, tmp_path):
        assert is_paid_user("nobody", base_path=tmp_path) is False
