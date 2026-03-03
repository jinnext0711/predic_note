"""
netkeiba.com からレースデータを取得する RaceDataFetcher 実装。

負荷配慮:
- リクエスト間隔: デフォルト3秒（最低2秒）
- 増分取得: 取得済みrace_idはスキップ
- User-Agent: 適切なUA設定
"""
import logging
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Set

import requests

from .fetcher import RaceDataFetcher
from .netkeiba_parser import parse_race_result_page, parse_race_list_page
from .schema import Race, HorseEntry
from . import storage

logger = logging.getLogger(__name__)

# netkeiba のベースURL
BASE_URL = "https://db.netkeiba.com"

# デフォルトのリクエスト間隔（秒）
DEFAULT_INTERVAL = 3.0
MIN_INTERVAL = 2.0

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _generate_dates(start_date: date, end_date: date) -> List[date]:
    """開催がありえる日付（土日祝）を生成する。厳密な祝日判定は省略し全日を含める。"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


class NetkeibaRaceDataFetcher(RaceDataFetcher):
    """
    netkeiba.com からレース結果データを取得する。

    Parameters
    ----------
    interval : float
        リクエスト間隔（秒）。デフォルト3秒。最低2秒。
    base_path : Path, optional
        データ保存先のベースパス。増分取得で既存チェックに使用。
    skip_existing : bool
        True の場合、既にデータが保存されているレースをスキップする。
    max_races : int, optional
        取得するレース数の上限。Noneで無制限。
    """

    def __init__(
        self,
        interval: float = DEFAULT_INTERVAL,
        base_path: Optional[Path] = None,
        skip_existing: bool = True,
        max_races: Optional[int] = None,
    ):
        self._interval = max(interval, MIN_INTERVAL)
        self._base_path = base_path
        self._skip_existing = skip_existing
        self._max_races = max_races
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._last_request_time = 0.0

        # 既存レースIDのキャッシュ
        self._existing_race_ids: Optional[Set[str]] = None
        # fetch_racesでエントリーも同時に取れるのでキャッシュする
        self._last_entries_cache: dict = {}

    def _wait(self):
        """リクエスト間隔を確保する。"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str) -> Optional[str]:
        """GETリクエストを実行し、HTMLテキストを返す。"""
        self._wait()
        try:
            resp = self._session.get(url, timeout=30)
            resp.raise_for_status()
            # netkeibaはEUC-JPの場合がある
            if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
                resp.encoding = "euc-jp"
            return resp.text
        except requests.RequestException as e:
            logger.warning("リクエスト失敗: %s - %s", url, e)
            return None

    def _load_existing_race_ids(self) -> Set[str]:
        """保存済みのレースIDセットを読み込む。"""
        if self._existing_race_ids is None:
            existing_races = storage.load_races(self._base_path)
            self._existing_race_ids = {r.race_id for r in existing_races}
        return self._existing_race_ids

    def _is_existing(self, race_id: str) -> bool:
        """指定レースが既に取得済みかチェックする。"""
        if not self._skip_existing:
            return False
        return race_id in self._load_existing_race_ids()

    def fetch_race_ids_for_date(self, target_date: date) -> List[str]:
        """指定日のレースID一覧を取得する。"""
        url = f"{BASE_URL}/race/list/{target_date.strftime('%Y%m%d')}/"
        html = self._get(url)
        if not html:
            return []
        return parse_race_list_page(html)

    def fetch_races(
        self,
        start_date: date,
        end_date: date,
        venue: Optional[str] = None,
        surface: Optional[str] = None,
        race_class: Optional[str] = None,
    ) -> List[Race]:
        """
        指定期間のレース一覧を取得する。

        日付ごとにレース一覧ページにアクセスし、各レースの結果ページからRaceを抽出する。
        取得済みレースはスキップ（増分対応）。
        """
        dates = _generate_dates(start_date, end_date)
        all_races: List[Race] = []
        fetched_count = 0

        for target_date in dates:
            # 上限チェック
            if self._max_races and fetched_count >= self._max_races:
                logger.info("上限 %d レースに到達。取得終了。", self._max_races)
                break

            race_ids = self.fetch_race_ids_for_date(target_date)
            if not race_ids:
                continue

            logger.info(
                "%s: %d レースを検出",
                target_date.isoformat(),
                len(race_ids),
            )

            for race_id in race_ids:
                if self._max_races and fetched_count >= self._max_races:
                    break

                # 増分取得: 既存はスキップ
                if self._is_existing(race_id):
                    logger.debug("スキップ（取得済み）: %s", race_id)
                    continue

                race, entries = self._fetch_race_detail(race_id)
                if race is None:
                    continue

                # フィルタ条件に一致しない場合はスキップ
                if venue and race.venue != venue:
                    continue
                if surface and race.surface != surface:
                    continue
                if race_class and race.race_class != race_class:
                    continue

                all_races.append(race)
                # エントリーも一緒に保存（パフォーマンスのため）
                self._last_entries_cache[race_id] = entries
                fetched_count += 1

                logger.info(
                    "取得: %s %s %s %dm %s (%d頭)",
                    race_id, race.venue, race.surface, race.distance,
                    race.race_class, len(entries),
                )

        return all_races

    def fetch_race_entries(self, race_id: str) -> List[HorseEntry]:
        """
        指定レースの出走馬一覧を取得する。

        fetch_racesで既に取得済みの場合はキャッシュから返す。
        """
        # キャッシュにあればそこから返す
        if race_id in self._last_entries_cache:
            return self._last_entries_cache.pop(race_id)

        # 個別取得
        _, entries = self._fetch_race_detail(race_id)
        return entries

    def _fetch_race_detail(self, race_id: str):
        """レース結果ページを取得・パースする。"""
        url = f"{BASE_URL}/race/{race_id}/"
        html = self._get(url)
        if not html:
            return None, []
        return parse_race_result_page(html, race_id)

