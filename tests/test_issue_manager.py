"""issue_manager モジュールのテスト。

gh CLI 呼び出しはすべてモック化する。
"""
import json
import subprocess
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tracking.issue_manager import (
    COMPLETED_STATUSES,
    DEFAULT_REPO,
    STATUS_ICONS,
    STATUS_LABELS,
    PredictionIssue,
    RaceTrackingEntry,
    RaceTrackingStatus,
    _extract_race_number,
    close_prediction_issue,
    create_prediction_issue,
    find_existing_issue,
    get_or_create_issue,
    update_race_status,
)


# ---------------------------------------------------------------------------
# RaceTrackingEntry テスト
# ---------------------------------------------------------------------------


class TestRaceTrackingEntry:
    """RaceTrackingEntry のテスト。"""

    def test_to_checkbox_pending(self):
        """PENDING ステータスのチェックボックス行"""
        entry = RaceTrackingEntry(
            race_id="202506010101",
            race_name="テストレース",
            venue="中山",
            race_number=1,
            status=RaceTrackingStatus.PENDING,
        )
        line = entry.to_checkbox_line()
        assert line.startswith("- [ ]")
        assert "⬜" in line
        assert "中山" in line
        assert "1R" in line
        assert "テストレース" in line
        assert "(未処理)" in line
        assert "<!-- 202506010101 -->" in line

    def test_to_checkbox_completed(self):
        """DRAFT_SAVED ステータスのチェックボックス行（完了）"""
        entry = RaceTrackingEntry(
            race_id="202506010112",
            race_name="メインレース",
            venue="阪神",
            race_number=12,
            status=RaceTrackingStatus.DRAFT_SAVED,
        )
        line = entry.to_checkbox_line()
        assert line.startswith("- [x]")
        assert "✅" in line
        assert "(予想完了)" in line

    def test_to_checkbox_skipped(self):
        """SKIPPED_UNCONFIRMED ステータスのチェックボックス行"""
        entry = RaceTrackingEntry(
            race_id="202506010103",
            race_name="未確定レース",
            venue="中京",
            race_number=3,
            status=RaceTrackingStatus.SKIPPED_UNCONFIRMED,
        )
        line = entry.to_checkbox_line()
        assert line.startswith("- [x]")  # 完了扱い
        assert "⚠️" in line
        assert "(出馬表未確定)" in line

    def test_to_checkbox_error_with_message(self):
        """ERROR ステータスにエラーメッセージ付き"""
        entry = RaceTrackingEntry(
            race_id="202506010105",
            race_name="エラーレース",
            venue="中山",
            race_number=5,
            status=RaceTrackingStatus.ERROR,
            error_message="接続タイムアウト",
        )
        line = entry.to_checkbox_line()
        assert line.startswith("- [x]")
        assert "❌" in line
        assert "(エラー)" in line
        assert "接続タイムアウト" in line

    def test_to_checkbox_data_collected(self):
        """DATA_COLLECTED ステータス（進行中 = 未チェック）"""
        entry = RaceTrackingEntry(
            race_id="202506010106",
            race_name="進行中レース",
            venue="阪神",
            race_number=6,
            status=RaceTrackingStatus.DATA_COLLECTED,
        )
        line = entry.to_checkbox_line()
        assert line.startswith("- [ ]")  # 進行中
        assert "📥" in line
        assert "(データ収集完了)" in line


# ---------------------------------------------------------------------------
# PredictionIssue テスト
# ---------------------------------------------------------------------------


class TestPredictionIssue:
    """PredictionIssue のテスト。"""

    def _make_entries(self):
        """テスト用エントリーリストを作成する。"""
        return [
            RaceTrackingEntry("202506010101", "1Rレース", "中山", 1),
            RaceTrackingEntry("202506010102", "2Rレース", "中山", 2),
            RaceTrackingEntry("202506020101", "1Rレース", "阪神", 1),
        ]

    def test_title_single_venue(self):
        """1会場のタイトル"""
        issue = PredictionIssue(
            race_date="2026-03-07",
            entries=[
                RaceTrackingEntry("r1", "レース1", "中山", 1),
                RaceTrackingEntry("r2", "レース2", "中山", 2),
            ],
        )
        assert issue.title == "[予想] 2026-03-07 中山"

    def test_title_multiple_venues(self):
        """複数会場のタイトル"""
        issue = PredictionIssue(
            race_date="2026-03-07",
            entries=self._make_entries(),
        )
        assert "中山" in issue.title
        assert "阪神" in issue.title
        assert "[予想] 2026-03-07" in issue.title

    def test_title_no_entries(self):
        """エントリーなしのタイトル"""
        issue = PredictionIssue(race_date="2026-03-07")
        assert issue.title == "[予想] 2026-03-07 未定"

    def test_build_body_structure(self):
        """本文の基本構造"""
        issue = PredictionIssue(
            race_date="2026-03-07",
            entries=self._make_entries(),
        )
        body = issue.build_body()
        # ヘッダー
        assert "# 2026-03-07 予想進捗" in body
        assert "**対象日**: 2026-03-07" in body
        # 会場見出し
        assert "## 中山" in body
        assert "## 阪神" in body
        # チェックボックス
        assert "- [ ]" in body
        # サマリー
        assert "## サマリー" in body
        assert "全レース数: 3" in body
        assert "残り: 3" in body

    def test_build_body_with_completed(self):
        """完了レースを含む本文のサマリー"""
        entries = self._make_entries()
        entries[0].status = RaceTrackingStatus.DRAFT_SAVED
        entries[1].status = RaceTrackingStatus.SKIPPED_UNCONFIRMED
        issue = PredictionIssue(
            race_date="2026-03-07",
            entries=entries,
        )
        body = issue.build_body()
        assert "完了: 2" in body
        assert "出馬表未確定スキップ: 1" in body
        assert "残り: 1" in body

    def test_build_body_venues_sorted(self):
        """会場がソートされている"""
        entries = [
            RaceTrackingEntry("r1", "レース1", "中山", 1),
            RaceTrackingEntry("r2", "レース2", "阪神", 1),
            RaceTrackingEntry("r3", "レース3", "中京", 1),
        ]
        issue = PredictionIssue(race_date="2026-03-07", entries=entries)
        body = issue.build_body()
        # 中京 < 中山 < 阪神 の順でソート
        idx_chukyo = body.index("## 中京")
        idx_nakayama = body.index("## 中山")
        idx_hanshin = body.index("## 阪神")
        assert idx_chukyo < idx_nakayama < idx_hanshin


# ---------------------------------------------------------------------------
# ユーティリティ関数テスト
# ---------------------------------------------------------------------------


class TestExtractRaceNumber:
    """_extract_race_number のテスト。"""

    def test_standard_race_id(self):
        """標準的なrace_id"""
        assert _extract_race_number("202506010101") == 1
        assert _extract_race_number("202506010112") == 12
        assert _extract_race_number("202506020205") == 5

    def test_short_race_id(self):
        """短すぎるrace_id"""
        assert _extract_race_number("2025") == 0
        assert _extract_race_number("") == 0

    def test_invalid_race_id(self):
        """数値でない部分を含むrace_id"""
        assert _extract_race_number("2025060101XX") == 0


# ---------------------------------------------------------------------------
# gh CLI モックテスト
# ---------------------------------------------------------------------------


class TestCreatePredictionIssue:
    """create_prediction_issue のテスト（gh モック）。"""

    @patch("tracking.issue_manager._run_gh")
    def test_create_issue(self, mock_run_gh):
        """Issue 作成が正しく行われる"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="https://github.com/jinnext0711/predic_note/issues/42\n",
        )

        races = [
            {"race_id": "202506010101", "race_name": "1Rレース", "venue": "中山"},
            {"race_id": "202506010102", "race_name": "2Rレース", "venue": "中山"},
        ]
        issue = create_prediction_issue("2026-03-07", races)

        assert issue.issue_number == 42
        assert issue.race_date == "2026-03-07"
        assert len(issue.entries) == 2

        # gh コマンドの呼び出し確認
        mock_run_gh.assert_called_once()
        call_args = mock_run_gh.call_args[0][0]
        assert "issue" in call_args
        assert "create" in call_args
        assert "--label" in call_args

    @patch("tracking.issue_manager._run_gh")
    def test_create_issue_parse_failure(self, mock_run_gh):
        """Issue 番号が抽出できない場合"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="unexpected output\n"
        )
        races = [
            {"race_id": "202506010101", "race_name": "1R", "venue": "中山"},
        ]
        issue = create_prediction_issue("2026-03-07", races)
        assert issue.issue_number is None


class TestUpdateRaceStatus:
    """update_race_status のテスト（gh モック）。"""

    @patch("tracking.issue_manager._run_gh")
    def test_update_status(self, mock_run_gh):
        """ステータス更新が正しく行われる"""
        # 最初の呼び出し: issue view
        existing_body = (
            "# テスト\n\n"
            "## 中山\n\n"
            "- [ ] ⬜ 中山 1R テストレース (未処理)"
            " <!-- 202506010101 -->\n"
        )
        mock_run_gh.side_effect = [
            # issue view
            subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout=json.dumps({"body": existing_body}),
            ),
            # issue edit
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="",
            ),
        ]

        result = update_race_status(
            issue_number=42,
            race_id="202506010101",
            status=RaceTrackingStatus.ANALYZED,
        )
        assert result is True
        assert mock_run_gh.call_count == 2

    @patch("tracking.issue_manager._run_gh")
    def test_update_status_not_found(self, mock_run_gh):
        """該当レースが見つからない場合"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps({"body": "# テスト\n"}),
        )
        result = update_race_status(
            issue_number=42,
            race_id="nonexistent_race",
            status=RaceTrackingStatus.ANALYZED,
        )
        assert result is False


class TestFindExistingIssue:
    """find_existing_issue のテスト（gh モック）。"""

    @patch("tracking.issue_manager._run_gh")
    def test_find_existing(self, mock_run_gh):
        """既存 Issue が見つかる場合"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([
                {"number": 10, "title": "[予想] 2026-03-07 中山・阪神"},
            ]),
        )
        result = find_existing_issue("2026-03-07")
        assert result == 10

    @patch("tracking.issue_manager._run_gh")
    def test_find_not_found(self, mock_run_gh):
        """Issue が見つからない場合"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=json.dumps([]),
        )
        result = find_existing_issue("2026-03-07")
        assert result is None

    @patch("tracking.issue_manager._run_gh")
    def test_find_gh_error(self, mock_run_gh):
        """gh コマンドがエラーの場合"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        result = find_existing_issue("2026-03-07")
        assert result is None


class TestGetOrCreateIssue:
    """get_or_create_issue のテスト（gh モック）。"""

    @patch("tracking.issue_manager.find_existing_issue")
    def test_reuse_existing(self, mock_find):
        """既存 Issue を再利用する"""
        mock_find.return_value = 99
        races = [
            {"race_id": "202506010101", "race_name": "1R", "venue": "中山"},
        ]
        issue = get_or_create_issue("2026-03-07", races)
        assert issue.issue_number == 99

    @patch("tracking.issue_manager.create_prediction_issue")
    @patch("tracking.issue_manager.find_existing_issue")
    def test_create_new(self, mock_find, mock_create):
        """Issue が存在しない場合は新規作成"""
        mock_find.return_value = None
        mock_create.return_value = PredictionIssue(
            race_date="2026-03-07", issue_number=100
        )
        races = [
            {"race_id": "202506010101", "race_name": "1R", "venue": "中山"},
        ]
        issue = get_or_create_issue("2026-03-07", races)
        assert issue.issue_number == 100
        mock_create.assert_called_once()


class TestClosePredictionIssue:
    """close_prediction_issue のテスト（gh モック）。"""

    @patch("tracking.issue_manager._run_gh")
    def test_close_issue(self, mock_run_gh):
        """Issue クローズ"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="",
        )
        result = close_prediction_issue(42, comment="全レース予想完了")
        assert result is True
        call_args = mock_run_gh.call_args[0][0]
        assert "close" in call_args
        assert "--comment" in call_args

    @patch("tracking.issue_manager._run_gh")
    def test_close_without_comment(self, mock_run_gh):
        """コメントなしでクローズ"""
        mock_run_gh.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="",
        )
        result = close_prediction_issue(42)
        assert result is True
        call_args = mock_run_gh.call_args[0][0]
        assert "--comment" not in call_args


# ---------------------------------------------------------------------------
# ステータス定数テスト
# ---------------------------------------------------------------------------


class TestStatusCompleteness:
    """全ステータスにアイコン・ラベルが定義されているか。"""

    def test_all_statuses_have_icons(self):
        """全 RaceTrackingStatus にアイコンが定義されている"""
        for status in RaceTrackingStatus:
            assert status in STATUS_ICONS, f"{status} のアイコンが未定義"

    def test_all_statuses_have_labels(self):
        """全 RaceTrackingStatus にラベルが定義されている"""
        for status in RaceTrackingStatus:
            assert status in STATUS_LABELS, f"{status} のラベルが未定義"

    def test_completed_statuses(self):
        """完了ステータスの定義確認"""
        assert RaceTrackingStatus.DRAFT_SAVED in COMPLETED_STATUSES
        assert RaceTrackingStatus.SKIPPED_UNCONFIRMED in COMPLETED_STATUSES
        assert RaceTrackingStatus.ERROR in COMPLETED_STATUSES
        assert RaceTrackingStatus.PENDING not in COMPLETED_STATUSES
        assert RaceTrackingStatus.ANALYZED not in COMPLETED_STATUSES
