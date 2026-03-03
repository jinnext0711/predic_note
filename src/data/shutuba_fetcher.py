"""
netkeiba.com から出馬表（未来レース）データを取得する ShutubaFetcher 実装。

対象URL:
- 開催日程: https://race.netkeiba.com/top/race_list.html?kaisai_date=YYYYMMDD
- 出馬表: https://race.netkeiba.com/race/shutuba.html?race_id={race_id}
- 馬の戦績: https://db.netkeiba.com/horse/{horse_id}/
- 騎手成績: https://db.netkeiba.com/jockey/result/recent/{jockey_id}/
- 調教師成績: https://db.netkeiba.com/trainer/result/recent/{trainer_id}/
- 単勝オッズ: https://race.netkeiba.com/odds/index.html?race_id={race_id}&type=b1

負荷配慮:
- リクエスト間隔: デフォルト3秒（最低2秒）
- User-Agent: 適切なUA設定
- リトライ: 最大3回（指数バックオフ）
"""
import logging
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from .shutuba_parser import (
    parse_race_calendar_page,
    parse_shutuba_page,
    parse_horse_history_page,
    parse_jockey_stats_page,
    parse_trainer_stats_page,
    parse_win_odds_page,
)
from .shutuba_schema import (
    HorseHistory,
    JockeyStats,
    OddsData,
    TrainerStats,
    UpcomingHorseEntry,
    UpcomingRaceWithEntries,
)

logger = logging.getLogger(__name__)

# ベースURL
RACE_BASE_URL = "https://race.netkeiba.com"
DB_BASE_URL = "https://db.netkeiba.com"

# リクエスト間隔の設定（秒）
DEFAULT_INTERVAL = 3.0
MIN_INTERVAL = 2.0

# リトライ設定
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # 指数バックオフの底（2秒, 4秒, 8秒）

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class ShutubaFetcher:
    """
    netkeiba.com から出馬表（未来レース）データを取得する。

    出馬表・馬の戦績・騎手成績・調教師成績・単勝オッズを一括取得し、
    UpcomingRaceWithEntries にまとめて返す。

    Parameters
    ----------
    interval : float
        リクエスト間隔（秒）。デフォルト3秒。最低2秒。
    base_path : Path, optional
        データ保存先のベースパス（将来のキャッシュ用）。
    max_races : int, optional
        取得するレース数の上限。Noneで無制限。
    """

    def __init__(
        self,
        interval: float = DEFAULT_INTERVAL,
        base_path: Optional[Path] = None,
        max_races: Optional[int] = None,
    ):
        self._interval = max(interval, MIN_INTERVAL)
        self._base_path = base_path
        self._max_races = max_races
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._last_request_time = 0.0

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------

    def _wait(self):
        """リクエスト間隔を確保する。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str) -> Optional[str]:
        """
        GETリクエストを実行し、HTMLテキストを返す。

        最大 MAX_RETRIES 回リトライする（指数バックオフ）。
        """
        for attempt in range(1, MAX_RETRIES + 1):
            self._wait()
            try:
                resp = self._session.get(url, timeout=30)
                resp.raise_for_status()
                # netkeibaはEUC-JPの場合がある
                if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
                    resp.encoding = "euc-jp"
                return resp.text
            except requests.RequestException as e:
                logger.warning(
                    "リクエスト失敗 (試行 %d/%d): %s - %s",
                    attempt, MAX_RETRIES, url, e,
                )
                if attempt < MAX_RETRIES:
                    # 指数バックオフで待機
                    backoff = RETRY_BACKOFF_BASE ** attempt
                    logger.info("%.1f秒後にリトライします...", backoff)
                    time.sleep(backoff)
                else:
                    logger.error(
                        "リクエスト最終失敗（%d回リトライ済み）: %s", MAX_RETRIES, url
                    )
        return None

    # ------------------------------------------------------------------
    # 個別データ取得メソッド
    # ------------------------------------------------------------------

    def fetch_race_calendar(self, target_date: date) -> List[str]:
        """
        指定日の開催日程からレースID一覧を取得する。

        Parameters
        ----------
        target_date : date
            対象日付

        Returns
        -------
        List[str]
            レースIDのリスト（中央競馬のみ）
        """
        date_str = target_date.strftime("%Y%m%d")
        url = f"{RACE_BASE_URL}/top/race_list.html?kaisai_date={date_str}"
        logger.info("開催日程を取得: %s (%s)", target_date.isoformat(), url)

        html = self._get(url)
        if not html:
            logger.warning("開催日程ページの取得に失敗: %s", target_date.isoformat())
            return []

        race_ids = parse_race_calendar_page(html)
        logger.info(
            "%s: %d レースを検出", target_date.isoformat(), len(race_ids)
        )
        return race_ids

    def fetch_shutuba(
        self, race_id: str
    ) -> Tuple[dict, List[UpcomingHorseEntry]]:
        """
        出馬表ページからレース情報とエントリー一覧を取得する。

        Parameters
        ----------
        race_id : str
            レースID（12桁）

        Returns
        -------
        Tuple[dict, List[UpcomingHorseEntry]]
            (レースメタ情報dict, 出走馬リスト)
            レースメタ情報: race_name, race_date, venue, surface, distance,
                           race_class, age_condition
        """
        url = f"{RACE_BASE_URL}/race/shutuba.html?race_id={race_id}"
        logger.info("出馬表を取得: race_id=%s", race_id)

        html = self._get(url)
        if not html:
            logger.warning("出馬表ページの取得に失敗: race_id=%s", race_id)
            return {}, []

        race_meta, entries = parse_shutuba_page(html, race_id)
        logger.info(
            "出馬表パース完了: race_id=%s, %d頭",
            race_id, len(entries),
        )
        return race_meta, entries

    def fetch_horse_history(
        self, horse_id: str, horse_name: str
    ) -> Optional[HorseHistory]:
        """
        馬の戦績ページから過去成績を取得する。

        Parameters
        ----------
        horse_id : str
            netkeiba馬ID
        horse_name : str
            馬名（ログ・結果格納用）

        Returns
        -------
        Optional[HorseHistory]
            馬の戦績サマリー。取得失敗時は None。
        """
        url = f"{DB_BASE_URL}/horse/{horse_id}/"
        logger.info("馬の戦績を取得: %s (id=%s)", horse_name, horse_id)

        html = self._get(url)
        if not html:
            logger.warning("馬の戦績ページの取得に失敗: %s (id=%s)", horse_name, horse_id)
            return None

        history = parse_horse_history_page(html, horse_id, horse_name)
        if history:
            logger.info(
                "馬の戦績パース完了: %s - %d戦%d勝 直近%d走",
                horse_name,
                history.total_runs,
                history.wins,
                len(history.recent_results),
            )
        else:
            logger.warning("馬の戦績パース失敗: %s (id=%s)", horse_name, horse_id)
        return history

    def fetch_jockey_stats(
        self, jockey_id: str, jockey_name: str
    ) -> Optional[JockeyStats]:
        """
        騎手の直近成績ページから成績サマリーを取得する。

        Parameters
        ----------
        jockey_id : str
            netkeiba騎手ID
        jockey_name : str
            騎手名（ログ・結果格納用）

        Returns
        -------
        Optional[JockeyStats]
            騎手成績サマリー。取得失敗時は None。
        """
        url = f"{DB_BASE_URL}/jockey/result/recent/{jockey_id}/"
        logger.info("騎手成績を取得: %s (id=%s)", jockey_name, jockey_id)

        html = self._get(url)
        if not html:
            logger.warning("騎手成績ページの取得に失敗: %s (id=%s)", jockey_name, jockey_id)
            return None

        stats = parse_jockey_stats_page(html, jockey_id, jockey_name)
        if stats:
            logger.info(
                "騎手成績パース完了: %s - %d戦%d勝 勝率%.1f%%",
                jockey_name,
                stats.year_runs,
                stats.year_wins,
                stats.year_win_rate * 100,
            )
        else:
            logger.warning("騎手成績パース失敗: %s (id=%s)", jockey_name, jockey_id)
        return stats

    def fetch_trainer_stats(
        self, trainer_id: str, trainer_name: str
    ) -> Optional[TrainerStats]:
        """
        調教師の直近成績ページから成績サマリーを取得する。

        Parameters
        ----------
        trainer_id : str
            netkeiba調教師ID
        trainer_name : str
            調教師名（ログ・結果格納用）

        Returns
        -------
        Optional[TrainerStats]
            調教師成績サマリー。取得失敗時は None。
        """
        url = f"{DB_BASE_URL}/trainer/result/recent/{trainer_id}/"
        logger.info("調教師成績を取得: %s (id=%s)", trainer_name, trainer_id)

        html = self._get(url)
        if not html:
            logger.warning(
                "調教師成績ページの取得に失敗: %s (id=%s)", trainer_name, trainer_id
            )
            return None

        stats = parse_trainer_stats_page(html, trainer_id, trainer_name)
        if stats:
            logger.info(
                "調教師成績パース完了: %s - %d戦%d勝 勝率%.1f%%",
                trainer_name,
                stats.year_runs,
                stats.year_wins,
                stats.year_win_rate * 100,
            )
        else:
            logger.warning("調教師成績パース失敗: %s (id=%s)", trainer_name, trainer_id)
        return stats

    def fetch_win_odds(self, race_id: str) -> Dict[int, float]:
        """
        単勝オッズページから馬番→オッズの辞書を取得する。

        Parameters
        ----------
        race_id : str
            レースID（12桁）

        Returns
        -------
        Dict[int, float]
            馬番 -> 単勝オッズ の辞書。取得失敗時は空辞書。
        """
        url = f"{RACE_BASE_URL}/odds/index.html?race_id={race_id}&type=b1"
        logger.info("単勝オッズを取得: race_id=%s", race_id)

        html = self._get(url)
        if not html:
            logger.warning("単勝オッズページの取得に失敗: race_id=%s", race_id)
            return {}

        odds_dict = parse_win_odds_page(html)
        logger.info(
            "単勝オッズパース完了: race_id=%s, %d頭分",
            race_id, len(odds_dict),
        )
        return odds_dict

    # ------------------------------------------------------------------
    # 統合取得メソッド
    # ------------------------------------------------------------------

    def fetch_full_race_data(self, race_id: str) -> Optional[UpcomingRaceWithEntries]:
        """
        1レース分の全データを統合取得する。

        出馬表 → 各馬の戦績 → 騎手成績 → 調教師成績 → 単勝オッズ
        の順にデータを取得し、UpcomingRaceWithEntries にまとめる。
        騎手・調教師は同一人物が複数馬に騎乗/管理する場合、重複リクエストを排除する。

        Parameters
        ----------
        race_id : str
            レースID（12桁）

        Returns
        -------
        Optional[UpcomingRaceWithEntries]
            全データを含むレース情報。出馬表取得失敗時は None。
        """
        logger.info("=== レース全データ取得開始: race_id=%s ===", race_id)

        # (1) 出馬表を取得
        race_meta, entries = self.fetch_shutuba(race_id)
        if not entries:
            logger.warning("出馬表が空のためスキップ: race_id=%s", race_id)
            return None

        # (2) 各馬の戦績を取得
        horse_histories: Dict[str, HorseHistory] = {}
        for entry in entries:
            if entry.horse_id in horse_histories:
                # 同一馬が複数回出ることはないが念のため
                continue
            history = self.fetch_horse_history(entry.horse_id, entry.horse_name)
            if history:
                horse_histories[entry.horse_id] = history

        # (3) 騎手成績を取得（重複排除）
        jockey_stats: Dict[str, JockeyStats] = {}
        seen_jockey_ids: set = set()
        for entry in entries:
            if entry.jockey_id in seen_jockey_ids:
                continue
            seen_jockey_ids.add(entry.jockey_id)
            stats = self.fetch_jockey_stats(entry.jockey_id, entry.jockey_name)
            if stats:
                jockey_stats[entry.jockey_id] = stats

        # (4) 調教師成績を取得（重複排除）
        trainer_stats: Dict[str, TrainerStats] = {}
        seen_trainer_ids: set = set()
        for entry in entries:
            if entry.trainer_id in seen_trainer_ids:
                continue
            seen_trainer_ids.add(entry.trainer_id)
            stats = self.fetch_trainer_stats(entry.trainer_id, entry.trainer_name)
            if stats:
                trainer_stats[entry.trainer_id] = stats

        # (5) 単勝オッズを取得
        win_odds = self.fetch_win_odds(race_id)

        # OddsDataオブジェクトを構築（単勝のみ）
        odds_data: Optional[OddsData] = None
        if win_odds:
            from datetime import datetime

            odds_data = OddsData(
                race_id=race_id,
                win_odds=win_odds,
                timestamp=datetime.now().isoformat(),
            )

        # UpcomingRaceWithEntries を組み立て
        race_data = UpcomingRaceWithEntries(
            race_id=race_id,
            race_name=race_meta.get("race_name", ""),
            race_date=race_meta.get("race_date", ""),
            venue=race_meta.get("venue", ""),
            surface=race_meta.get("surface", ""),
            distance=race_meta.get("distance", 0),
            race_class=race_meta.get("race_class", ""),
            age_condition=race_meta.get("age_condition", ""),
            number_of_entries=len(entries),
            entries=entries,
            horse_histories=horse_histories,
            jockey_stats=jockey_stats,
            trainer_stats=trainer_stats,
            odds=odds_data,
        )

        logger.info(
            "=== レース全データ取得完了: %s %s %s%dm %d頭 ===",
            race_id,
            race_data.venue,
            race_data.surface,
            race_data.distance,
            len(entries),
        )
        return race_data

    def fetch_all_races_for_date(
        self, target_date: date
    ) -> List[UpcomingRaceWithEntries]:
        """
        指定日の全レースの全データを取得する。

        開催日程からレースID一覧を取得し、各レースについて fetch_full_race_data を
        順次実行する。max_races が設定されている場合はその数で打ち切る。

        Parameters
        ----------
        target_date : date
            対象日付

        Returns
        -------
        List[UpcomingRaceWithEntries]
            対象日の全レースデータリスト
        """
        logger.info(
            "========================================\n"
            "  %s の全レースデータ取得開始\n"
            "========================================",
            target_date.isoformat(),
        )

        # 開催日程からレースID一覧を取得
        race_ids = self.fetch_race_calendar(target_date)
        if not race_ids:
            logger.warning(
                "%s: レースが見つかりませんでした", target_date.isoformat()
            )
            return []

        # 上限の適用
        if self._max_races is not None and len(race_ids) > self._max_races:
            logger.info(
                "上限 %d レースを適用（全 %d レース中）",
                self._max_races, len(race_ids),
            )
            race_ids = race_ids[: self._max_races]

        # 各レースのデータを取得
        all_races: List[UpcomingRaceWithEntries] = []
        for i, race_id in enumerate(race_ids, 1):
            logger.info(
                "--- レース %d/%d: race_id=%s ---",
                i, len(race_ids), race_id,
            )
            race_data = self.fetch_full_race_data(race_id)
            if race_data:
                all_races.append(race_data)
            else:
                logger.warning(
                    "レースデータ取得失敗（スキップ）: race_id=%s", race_id
                )

        logger.info(
            "========================================\n"
            "  %s: %d/%d レースの取得完了\n"
            "========================================",
            target_date.isoformat(),
            len(all_races),
            len(race_ids),
        )
        return all_races
