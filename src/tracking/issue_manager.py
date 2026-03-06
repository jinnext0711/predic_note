"""
GitHub Issue による予想進捗トラッキング。

gh CLI を使用して predic_note リポジトリに Issue を作成・更新し、
各レースの予想進捗をチェックボックスで管理する。

使い方:
    from tracking.issue_manager import (
        create_prediction_issue,
        update_race_status,
        RaceTrackingStatus,
    )

    # Issue 作成
    issue = create_prediction_issue("2026-03-07", races)

    # ステータス更新
    update_race_status(issue.issue_number, race_id, RaceTrackingStatus.ANALYZED)
"""
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# GitHub リポジトリ設定
DEFAULT_REPO = "jinnext0711/predic_note"


class RaceTrackingStatus(str, Enum):
    """レースの予想進捗ステータス。"""

    PENDING = "pending"                           # 未処理
    DATA_COLLECTED = "data_collected"             # データ収集完了
    ANALYZED = "analyzed"                         # 分析完了
    REVIEWED = "reviewed"                         # レビュー完了
    ARTICLE_WRITTEN = "article_written"           # 記事作成完了
    DRAFT_SAVED = "draft_saved"                   # 下書き保存完了
    SKIPPED_UNCONFIRMED = "skipped_unconfirmed"   # 出馬表未確定でスキップ
    ERROR = "error"                               # エラー


# ステータスに対応する表示アイコン
STATUS_ICONS: Dict[str, str] = {
    RaceTrackingStatus.PENDING: "⬜",
    RaceTrackingStatus.DATA_COLLECTED: "📥",
    RaceTrackingStatus.ANALYZED: "📊",
    RaceTrackingStatus.REVIEWED: "👀",
    RaceTrackingStatus.ARTICLE_WRITTEN: "✏️",
    RaceTrackingStatus.DRAFT_SAVED: "✅",
    RaceTrackingStatus.SKIPPED_UNCONFIRMED: "⚠️",
    RaceTrackingStatus.ERROR: "❌",
}

# ステータスの日本語表示
STATUS_LABELS: Dict[str, str] = {
    RaceTrackingStatus.PENDING: "未処理",
    RaceTrackingStatus.DATA_COLLECTED: "データ収集完了",
    RaceTrackingStatus.ANALYZED: "分析完了",
    RaceTrackingStatus.REVIEWED: "レビュー完了",
    RaceTrackingStatus.ARTICLE_WRITTEN: "記事作成完了",
    RaceTrackingStatus.DRAFT_SAVED: "予想完了",
    RaceTrackingStatus.SKIPPED_UNCONFIRMED: "出馬表未確定",
    RaceTrackingStatus.ERROR: "エラー",
}

# 完了とみなすステータス（チェックボックスが [x] になる）
COMPLETED_STATUSES = {
    RaceTrackingStatus.DRAFT_SAVED,
    RaceTrackingStatus.SKIPPED_UNCONFIRMED,
    RaceTrackingStatus.ERROR,
}


@dataclass
class RaceTrackingEntry:
    """1レースの追跡エントリー。"""

    race_id: str
    race_name: str
    venue: str
    race_number: int     # レース番号（1-12）
    status: RaceTrackingStatus = RaceTrackingStatus.PENDING
    error_message: str = ""

    def to_checkbox_line(self) -> str:
        """Issue 本文用のチェックボックス行を生成する。"""
        checked = "x" if self.status in COMPLETED_STATUSES else " "
        icon = STATUS_ICONS.get(self.status, "⬜")
        label = STATUS_LABELS.get(self.status, "未処理")
        line = (
            f"- [{checked}] {icon} {self.venue} {self.race_number}R"
            f" {self.race_name} ({label})"
        )
        if self.error_message:
            line += f" - {self.error_message}"
        # race_id をHTMLコメントとして埋め込み（更新時の照合用）
        line += f" <!-- {self.race_id} -->"
        return line


@dataclass
class PredictionIssue:
    """1日分の予想追跡 Issue。"""

    race_date: str                           # YYYY-MM-DD
    issue_number: Optional[int] = None       # GitHub Issue 番号
    entries: List[RaceTrackingEntry] = field(default_factory=list)
    repo: str = DEFAULT_REPO

    @property
    def title(self) -> str:
        """Issue タイトルを生成する。"""
        venues = sorted(set(e.venue for e in self.entries))
        venue_str = "・".join(venues) if venues else "未定"
        return f"[予想] {self.race_date} {venue_str}"

    def build_body(self) -> str:
        """Issue 本文を生成する。"""
        lines = [
            f"# {self.race_date} 予想進捗",
            "",
            f"**対象日**: {self.race_date}",
        ]

        # 会場ごとにグループ化
        venues: Dict[str, List[RaceTrackingEntry]] = {}
        for entry in self.entries:
            venues.setdefault(entry.venue, []).append(entry)

        for venue_name in sorted(venues.keys()):
            venue_entries = sorted(
                venues[venue_name], key=lambda e: e.race_number
            )
            lines.append("")
            lines.append(f"## {venue_name}")
            lines.append("")
            for entry in venue_entries:
                lines.append(entry.to_checkbox_line())

        # サマリー
        total = len(self.entries)
        completed = sum(
            1 for e in self.entries if e.status in COMPLETED_STATUSES
        )
        skipped = sum(
            1
            for e in self.entries
            if e.status == RaceTrackingStatus.SKIPPED_UNCONFIRMED
        )
        errors = sum(
            1 for e in self.entries if e.status == RaceTrackingStatus.ERROR
        )

        lines.extend([
            "",
            "---",
            "",
            "## サマリー",
            f"- 全レース数: {total}",
            f"- 完了: {completed}",
            f"- 出馬表未確定スキップ: {skipped}",
            f"- エラー: {errors}",
            f"- 残り: {total - completed}",
        ])

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# gh CLI ラッパー関数
# ---------------------------------------------------------------------------


def _run_gh(
    args: List[str], check: bool = True
) -> subprocess.CompletedProcess:
    """gh CLI コマンドを実行する。"""
    cmd = ["gh"] + args
    logger.debug("gh コマンド実行: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(
            "gh コマンド失敗: %s\nstderr: %s", " ".join(cmd), e.stderr
        )
        raise
    except FileNotFoundError:
        logger.error(
            "gh CLI が見つかりません。"
            "'brew install gh' でインストールしてください。"
        )
        raise


def _extract_race_number(race_id: str) -> int:
    """
    race_id からレース番号を抽出する。

    形式: YYYY{venue_code:2}{kai:2}{day:2}{race_num:2}
    例: 202506010101 → レース番号 01
    """
    if len(race_id) >= 12:
        try:
            return int(race_id[10:12])
        except ValueError:
            return 0
    return 0


# ---------------------------------------------------------------------------
# Issue 操作関数
# ---------------------------------------------------------------------------


def create_prediction_issue(
    race_date: str,
    races: List[dict],
    repo: str = DEFAULT_REPO,
) -> PredictionIssue:
    """
    予想追跡用の GitHub Issue を作成する。

    Parameters
    ----------
    race_date : str
        対象日 (YYYY-MM-DD)
    races : List[dict]
        レース情報リスト。各要素は race_id, race_name, venue を含む
    repo : str
        対象リポジトリ

    Returns
    -------
    PredictionIssue
        作成された Issue 情報
    """
    # エントリー構築
    entries = []
    for race_info in races:
        race_id = race_info["race_id"]
        entry = RaceTrackingEntry(
            race_id=race_id,
            race_name=race_info.get("race_name", ""),
            venue=race_info.get("venue", "不明"),
            race_number=_extract_race_number(race_id),
        )
        entries.append(entry)

    issue = PredictionIssue(
        race_date=race_date, entries=entries, repo=repo
    )

    # gh CLI で Issue 作成
    result = _run_gh([
        "issue", "create",
        "--repo", repo,
        "--title", issue.title,
        "--body", issue.build_body(),
        "--label", "prediction",
    ])

    # Issue 番号を抽出（gh issue create の出力は URL 形式）
    url = result.stdout.strip()
    m = re.search(r"/issues/(\d+)", url)
    if m:
        issue.issue_number = int(m.group(1))
        logger.info(
            "Issue 作成完了: #%d %s", issue.issue_number, issue.title
        )
    else:
        logger.warning("Issue 番号の抽出に失敗: %s", url)

    return issue


def update_race_status(
    issue_number: int,
    race_id: str,
    status: RaceTrackingStatus,
    error_message: str = "",
    repo: str = DEFAULT_REPO,
) -> bool:
    """
    既存 Issue 内の特定レースのステータスを更新する。

    Issue 本文を取得し、race_id（HTMLコメント内）で該当行を特定して
    新しいステータスに書き換えて更新する。

    Parameters
    ----------
    issue_number : int
        GitHub Issue 番号
    race_id : str
        対象レースID
    status : RaceTrackingStatus
        新しいステータス
    error_message : str
        エラーメッセージ（status=ERROR の場合）
    repo : str
        対象リポジトリ

    Returns
    -------
    bool
        更新成功なら True
    """
    # 現在の Issue 本文を取得
    result = _run_gh([
        "issue", "view", str(issue_number),
        "--repo", repo,
        "--json", "body",
    ])
    body_data = json.loads(result.stdout)
    current_body = body_data.get("body", "")

    # race_id で該当行を検索して更新
    icon = STATUS_ICONS.get(status, "⬜")
    label = STATUS_LABELS.get(status, "未処理")
    checked = "x" if status in COMPLETED_STATUSES else " "

    lines = current_body.split("\n")
    updated = False
    for i, line in enumerate(lines):
        # HTMLコメント内の race_id で照合
        if f"<!-- {race_id} -->" in line and line.strip().startswith("- ["):
            # 既存行からvenue, race_number, race_nameを抽出
            m = re.match(
                r"- \[[ x]\] .+? (\S+) (\d+)R (.+?) \(.+?\)"
                r"(?: - .+?)? <!-- .+ -->",
                line.strip(),
            )
            if m:
                venue = m.group(1)
                race_number = m.group(2)
                race_name = m.group(3)
                new_line = (
                    f"- [{checked}] {icon} {venue} {race_number}R"
                    f" {race_name} ({label})"
                )
                if error_message:
                    new_line += f" - {error_message}"
                new_line += f" <!-- {race_id} -->"
                lines[i] = new_line
                updated = True
                break

    if not updated:
        logger.warning(
            "Issue #%d 内にレース %s が見つかりません",
            issue_number,
            race_id,
        )
        return False

    # Issue 本文を更新
    new_body = "\n".join(lines)
    _run_gh([
        "issue", "edit", str(issue_number),
        "--repo", repo,
        "--body", new_body,
    ])
    logger.info(
        "Issue #%d レース %s のステータスを %s に更新",
        issue_number,
        race_id,
        label,
    )
    return True


def close_prediction_issue(
    issue_number: int,
    comment: str = "",
    repo: str = DEFAULT_REPO,
) -> bool:
    """
    予想完了後に Issue をクローズする。

    Parameters
    ----------
    issue_number : int
        GitHub Issue 番号
    comment : str
        クローズ時のコメント
    repo : str
        対象リポジトリ

    Returns
    -------
    bool
        クローズ成功なら True
    """
    args = [
        "issue", "close", str(issue_number),
        "--repo", repo,
    ]
    if comment:
        args.extend(["--comment", comment])

    _run_gh(args)
    logger.info("Issue #%d をクローズしました", issue_number)
    return True


def find_existing_issue(
    race_date: str,
    repo: str = DEFAULT_REPO,
) -> Optional[int]:
    """
    指定日の既存予想 Issue を検索する。

    Parameters
    ----------
    race_date : str
        対象日 (YYYY-MM-DD)
    repo : str
        対象リポジトリ

    Returns
    -------
    Optional[int]
        既存 Issue 番号。見つからなければ None
    """
    result = _run_gh(
        [
            "issue", "list",
            "--repo", repo,
            "--search", f"[予想] {race_date} in:title",
            "--state", "open",
            "--json", "number,title",
        ],
        check=False,
    )

    if result.returncode != 0:
        return None

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    for issue in issues:
        if race_date in issue.get("title", ""):
            return issue["number"]
    return None


def get_or_create_issue(
    race_date: str,
    races: List[dict],
    repo: str = DEFAULT_REPO,
) -> PredictionIssue:
    """
    既存の Issue を探すか、なければ新規作成する。

    Parameters
    ----------
    race_date : str
        対象日 (YYYY-MM-DD)
    races : List[dict]
        レース情報リスト
    repo : str
        対象リポジトリ

    Returns
    -------
    PredictionIssue
        Issue 情報
    """
    existing_number = find_existing_issue(race_date, repo)
    if existing_number is not None:
        logger.info("既存の Issue #%d を使用します", existing_number)
        entries = []
        for race_info in races:
            race_id = race_info["race_id"]
            entries.append(
                RaceTrackingEntry(
                    race_id=race_id,
                    race_name=race_info.get("race_name", ""),
                    venue=race_info.get("venue", "不明"),
                    race_number=_extract_race_number(race_id),
                )
            )
        return PredictionIssue(
            race_date=race_date,
            issue_number=existing_number,
            entries=entries,
            repo=repo,
        )
    return create_prediction_issue(race_date, races, repo)
