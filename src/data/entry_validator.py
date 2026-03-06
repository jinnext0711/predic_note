"""
出馬表（エントリー）の確定状態を検証するモジュール。

出馬表が未確定（騎手未定、斤量未設定、出走頭数不足など）の場合を検出し、
予想対象から除外するための判定を行う。

判定基準は docs/PREDICTION_POLICY.md「出馬表確定チェック」に準拠する。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .shutuba_schema import UpcomingHorseEntry, UpcomingRaceWithEntries


class EntryStatus(str, Enum):
    """出馬表の確定状態。"""

    CONFIRMED = "confirmed"           # 確定済み（予想可能）
    PARTIALLY_CONFIRMED = "partial"   # 一部未確定（警告付きで予想可能）
    UNCONFIRMED = "unconfirmed"       # 未確定（予想不可）
    NOT_AVAILABLE = "not_available"   # 出馬表自体が未公開


@dataclass
class EntryIssue:
    """エントリーの個別問題。"""

    horse_number: int
    horse_name: str
    issue_type: str    # "jockey_missing", "weight_carry_missing", "horse_id_missing"
    description: str   # 日本語の説明

    def to_dict(self) -> dict:
        return {
            "horse_number": self.horse_number,
            "horse_name": self.horse_name,
            "issue_type": self.issue_type,
            "description": self.description,
        }


@dataclass
class EntryValidationResult:
    """出馬表の検証結果。"""

    race_id: str
    race_name: str
    status: EntryStatus
    issues: List[EntryIssue] = field(default_factory=list)
    summary: str = ""   # 日本語の検証サマリー

    @property
    def is_analyzable(self) -> bool:
        """分析可能かどうかを返す。"""
        return self.status in (
            EntryStatus.CONFIRMED,
            EntryStatus.PARTIALLY_CONFIRMED,
        )

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_name": self.race_name,
            "status": self.status.value,
            "is_analyzable": self.is_analyzable,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# 検証定数
# ---------------------------------------------------------------------------

# レース成立最低頭数
MIN_ENTRIES_FOR_RACE = 5

# 騎手未定の割合閾値（これ以上で未確定）
MAX_MISSING_JOCKEYS_RATIO = 0.3

# 騎手未定の割合閾値（これ以上で一部未確定）
PARTIAL_MISSING_JOCKEYS_RATIO = 0.1


# ---------------------------------------------------------------------------
# エントリー個別チェック関数
# ---------------------------------------------------------------------------


def _check_jockey_missing(entry: UpcomingHorseEntry) -> Optional[EntryIssue]:
    """騎手未定をチェックする。"""
    if not entry.jockey_name or not entry.jockey_id:
        return EntryIssue(
            horse_number=entry.horse_number,
            horse_name=entry.horse_name,
            issue_type="jockey_missing",
            description=f"{entry.horse_name}（{entry.horse_number}番）: 騎手未定",
        )
    return None


def _check_weight_carry(entry: UpcomingHorseEntry) -> Optional[EntryIssue]:
    """斤量未設定をチェックする。"""
    if entry.weight_carry <= 0.0:
        return EntryIssue(
            horse_number=entry.horse_number,
            horse_name=entry.horse_name,
            issue_type="weight_carry_missing",
            description=f"{entry.horse_name}（{entry.horse_number}番）: 斤量未設定",
        )
    return None


def _check_horse_id(entry: UpcomingHorseEntry) -> Optional[EntryIssue]:
    """horse_id 未設定をチェックする。"""
    if not entry.horse_id:
        return EntryIssue(
            horse_number=entry.horse_number,
            horse_name=entry.horse_name,
            issue_type="horse_id_missing",
            description=f"{entry.horse_name}（{entry.horse_number}番）: 馬ID未設定（戦績取得不可）",
        )
    return None


# ---------------------------------------------------------------------------
# メインの検証関数
# ---------------------------------------------------------------------------


def validate_entries(race: UpcomingRaceWithEntries) -> EntryValidationResult:
    """
    レースの出馬表を検証し、確定状態を判定する。

    判定基準（PREDICTION_POLICY.md 準拠）:
    1. エントリーが0頭 → NOT_AVAILABLE
    2. エントリーが MIN_ENTRIES_FOR_RACE 未満 → UNCONFIRMED
    3. 騎手未定の割合が MAX_MISSING_JOCKEYS_RATIO 以上 → UNCONFIRMED
    4. 騎手未定の割合が PARTIAL_MISSING_JOCKEYS_RATIO 以上 → PARTIALLY_CONFIRMED
    5. horse_id 未設定が1頭以上 → PARTIALLY_CONFIRMED
    6. 斤量未設定が1頭以上 → PARTIALLY_CONFIRMED
    7. 上記いずれにも該当しない → CONFIRMED

    Parameters
    ----------
    race : UpcomingRaceWithEntries
        検証対象のレースデータ

    Returns
    -------
    EntryValidationResult
        検証結果
    """
    issues: List[EntryIssue] = []
    entries = race.entries

    # チェック1: エントリー数が0
    if not entries:
        return EntryValidationResult(
            race_id=race.race_id,
            race_name=race.race_name,
            status=EntryStatus.NOT_AVAILABLE,
            summary="出馬表が取得できませんでした。",
        )

    # チェック2: エントリー数不足
    if len(entries) < MIN_ENTRIES_FOR_RACE:
        return EntryValidationResult(
            race_id=race.race_id,
            race_name=race.race_name,
            status=EntryStatus.UNCONFIRMED,
            summary=(
                f"出走頭数が不足しています"
                f"（{len(entries)}頭 / 最低{MIN_ENTRIES_FOR_RACE}頭）。"
            ),
        )

    # チェック3: 各エントリーの個別検証
    for entry in entries:
        for check_fn in [_check_jockey_missing, _check_weight_carry, _check_horse_id]:
            issue = check_fn(entry)
            if issue:
                issues.append(issue)

    # チェック4: 集計による判定
    jockey_missing_count = sum(
        1 for i in issues if i.issue_type == "jockey_missing"
    )
    horse_id_missing_count = sum(
        1 for i in issues if i.issue_type == "horse_id_missing"
    )
    weight_missing_count = sum(
        1 for i in issues if i.issue_type == "weight_carry_missing"
    )
    jockey_missing_ratio = jockey_missing_count / len(entries)

    # 未確定判定（騎手未定が30%以上）
    if jockey_missing_ratio >= MAX_MISSING_JOCKEYS_RATIO:
        return EntryValidationResult(
            race_id=race.race_id,
            race_name=race.race_name,
            status=EntryStatus.UNCONFIRMED,
            issues=issues,
            summary=(
                f"出馬表未確定: 騎手未定が多数"
                f"（{jockey_missing_count}/{len(entries)}頭）"
            ),
        )

    # 一部未確定判定
    if (
        jockey_missing_ratio >= PARTIAL_MISSING_JOCKEYS_RATIO
        or horse_id_missing_count > 0
        or weight_missing_count > 0
    ):
        summary_parts = []
        if jockey_missing_count > 0:
            summary_parts.append(f"騎手未定{jockey_missing_count}頭")
        if horse_id_missing_count > 0:
            summary_parts.append(f"馬ID未設定{horse_id_missing_count}頭")
        if weight_missing_count > 0:
            summary_parts.append(f"斤量未設定{weight_missing_count}頭")
        return EntryValidationResult(
            race_id=race.race_id,
            race_name=race.race_name,
            status=EntryStatus.PARTIALLY_CONFIRMED,
            issues=issues,
            summary="一部未確定: " + "、".join(summary_parts),
        )

    # 確定
    return EntryValidationResult(
        race_id=race.race_id,
        race_name=race.race_name,
        status=EntryStatus.CONFIRMED,
        summary="出馬表確定済み",
    )


def validate_all_races(
    races: List[UpcomingRaceWithEntries],
) -> List[EntryValidationResult]:
    """複数レースの出馬表をまとめて検証する。"""
    return [validate_entries(race) for race in races]
