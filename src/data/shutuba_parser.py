"""
netkeiba.com 出馬表（未来レース）関連ページのHTMLパーサー。

対象ページ:
  - 出馬表:       race.netkeiba.com/race/shutuba.html?race_id=XXX
  - 馬の戦績:     db.netkeiba.com/horse/{horse_id}/
  - レース一覧:   race.netkeiba.com/top/race_list.html?kaisai_date=YYYYMMDD
  - 単勝オッズ:   race.netkeiba.com/odds/index.html?race_id=XXX

既存の netkeiba_parser.py と同じパターンで、BeautifulSoup + lxml を使用。
"""
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from .shutuba_schema import (
    HorseHistory,
    JockeyStats,
    OddsData,
    PastRaceRecord,
    TrainerStats,
    UpcomingHorseEntry,
)
from .netkeiba_parser import VENUE_CODE_MAP, _parse_race_class, _parse_age_condition


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _safe_int(text: str) -> Optional[int]:
    """文字列を int に変換。変換不能なら None。"""
    try:
        return int(text.strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _safe_float(text: str) -> Optional[float]:
    """文字列を float に変換。変換不能なら None。"""
    try:
        return float(text.strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _extract_id_from_href(tag: Optional[Tag], pattern: str) -> str:
    """
    <a> タグの href から正規表現で ID を抽出する。
    見つからなければ空文字列を返す。
    """
    if tag is None:
        return ""
    a_tag = tag.find("a") if tag.name != "a" else tag
    if a_tag is None:
        return ""
    href = a_tag.get("href", "")
    m = re.search(pattern, href)
    return m.group(1) if m else ""


def _extract_venue_from_race_id(race_id: str) -> str:
    """race_id から競馬場名を取得。race_id形式: YYYY{venue_code}{kai}{day}{race_num}"""
    if len(race_id) >= 6:
        venue_code = race_id[4:6]
        return VENUE_CODE_MAP.get(venue_code, "不明")
    return "不明"


def _parse_distance_and_surface(course_text: str) -> Tuple[int, str]:
    """
    コース情報テキストから距離とコース種別を抽出する。
    出馬表ヘッダー例: 'ダ左1200m' / '芝右外2400m'
    """
    surface = "芝"
    if "ダ" in course_text:
        surface = "ダート"
    elif "障" in course_text:
        surface = "障害"

    m = re.search(r"(\d{3,5})\s*m", course_text)
    distance = int(m.group(1)) if m else 0
    return distance, surface


def _classify_running_style(corner_positions: List[Optional[str]]) -> str:
    """
    直近レースの通過順位から脚質を判定する。

    判定ロジック:
      - 各レースの最初のコーナー位置の平均を算出
      - 平均 <= 3.0  : 逃げ
      - 平均 <= 5.0  : 先行
      - 平均 <= 9.0  : 差し
      - それ以上      : 追込

    通過順データが不十分な場合は空文字列を返す。
    """
    first_positions: List[int] = []
    for pos_str in corner_positions:
        if not pos_str:
            continue
        parts = pos_str.split("-")
        if parts:
            val = _safe_int(parts[0])
            if val is not None:
                first_positions.append(val)

    if not first_positions:
        return ""

    avg = sum(first_positions) / len(first_positions)
    if avg <= 3.0:
        return "逃げ"
    elif avg <= 5.0:
        return "先行"
    elif avg <= 9.0:
        return "差し"
    else:
        return "追込"


def _distance_range_key(distance: int) -> str:
    """
    距離を距離カテゴリキーに変換する。
    例: 1200 -> "1000-1400", 1600 -> "1400-1800", 2400 -> "2200-2600"
    """
    if distance <= 1400:
        return "1000-1400"
    elif distance <= 1800:
        return "1400-1800"
    elif distance <= 2200:
        return "1800-2200"
    elif distance <= 2600:
        return "2200-2600"
    else:
        return "2600-"


# ---------------------------------------------------------------------------
# 1. 出馬表ページパーサー
# ---------------------------------------------------------------------------

def parse_shutuba_page(
    html: str, race_id: str
) -> Tuple[dict, List[UpcomingHorseEntry]]:
    """
    出馬表ページ (race.netkeiba.com/race/shutuba.html?race_id=XXX) をパースする。

    戻り値:
      - race_info: dict
          race_name, venue, surface, distance, race_class, age_condition
      - entries: List[UpcomingHorseEntry]

    取消馬は horse_name に '取' 等が付くが、リストには含めない（予測対象外）。
    """
    soup = BeautifulSoup(html, "lxml")

    # --- レース情報ヘッダーの抽出 ---
    race_info: dict = {
        "race_name": "",
        "venue": _extract_venue_from_race_id(race_id),
        "surface": "",
        "distance": 0,
        "race_class": "",
        "age_condition": "",
    }

    # レース名: RaceName クラスまたは h1 から取得
    race_name_tag = soup.find("div", class_="RaceName")
    if race_name_tag is None:
        race_name_tag = soup.find("h1", class_="RaceName")
    if race_name_tag:
        race_info["race_name"] = race_name_tag.get_text(strip=True)

    # コース情報（芝/ダート・距離）: RaceData01 内の span
    race_data_tag = soup.find("div", class_="RaceData01")
    if race_data_tag:
        course_text = race_data_tag.get_text()
        distance, surface = _parse_distance_and_surface(course_text)
        race_info["surface"] = surface
        race_info["distance"] = distance

    # クラス・年齢条件: RaceData02 内のテキスト
    race_data2_tag = soup.find("div", class_="RaceData02")
    info_text = race_data2_tag.get_text() if race_data2_tag else ""
    race_info["race_class"] = _parse_race_class(info_text, race_info["race_name"])
    race_info["age_condition"] = _parse_age_condition(info_text)

    # 障害レースはスキップ
    if race_info["surface"] == "障害":
        return race_info, []

    # --- 出走馬テーブルの抽出 ---
    entries: List[UpcomingHorseEntry] = []

    # 出馬表テーブル: class="Shutuba_Table" または class="ShutubaTable"
    table = soup.find("table", class_="Shutuba_Table")
    if table is None:
        table = soup.find("table", class_="ShutubaTable")
    if table is None:
        # race_table_01 形式のフォールバック
        table = soup.find("table", class_="race_table_01")
    if table is None:
        return race_info, entries

    rows = table.find_all("tr", class_="HorseList")
    if not rows:
        # HorseList クラスがない場合は全 tr を試行（ヘッダー行をスキップ）
        all_rows = table.find_all("tr")
        rows = all_rows[1:] if len(all_rows) > 1 else []

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 8:
            continue

        # 取消馬の判定: 行に "Cancel" クラスがある場合はスキップ
        row_classes = row.get("class", [])
        if any("Cancel" in c for c in row_classes):
            continue

        # 枠番
        frame_number = _safe_int(tds[0].get_text(strip=True))
        if frame_number is None:
            frame_number = 0

        # 馬番
        horse_number = _safe_int(tds[1].get_text(strip=True))
        if horse_number is None:
            continue  # 馬番が取れない行はスキップ

        # 馬名 & horse_id
        # 通常は tds[3] に馬名リンクがある（tds[2] がアイコン列の場合あり）
        horse_name = ""
        horse_id = ""
        # 馬名セルを探索: 各 td の中で /horse/ リンクを含むものを使用
        for td_idx in range(2, min(len(tds), 6)):
            td = tds[td_idx]
            horse_link = td.find("a", href=re.compile(r"/horse/(\w+)"))
            if horse_link:
                horse_name = horse_link.get_text(strip=True)
                m = re.search(r"/horse/(\w+)", horse_link.get("href", ""))
                if m:
                    horse_id = m.group(1).rstrip("/")
                break

        if not horse_name:
            continue

        # 取消馬判定: 馬名セル内に「取消」テキストがある場合
        parent_td_text = ""
        if horse_link:
            parent_td = horse_link.find_parent("td")
            parent_td_text = parent_td.get_text() if parent_td else ""
        if "取消" in parent_td_text or "除外" in parent_td_text:
            continue

        # 性齢
        sex_age = ""
        # 騎手名 & jockey_id
        jockey_name = ""
        jockey_id = ""
        # 斤量
        weight_carry: float = 0.0
        # 調教師名 & trainer_id
        trainer_name = ""
        trainer_id = ""
        # 馬体重
        horse_weight: Optional[str] = None
        # オッズ・人気
        morning_odds: Optional[float] = None
        popularity: Optional[int] = None

        # 各セルを順に走査して情報を抽出
        for td in tds:
            td_text = td.get_text(strip=True)
            td_classes = td.get("class", [])

            # 性齢セル: "Barei" または "Sex" クラス、または "牡3" / "牝4" 等のパターン
            if any(c in ("Barei", "Sex") for c in td_classes):
                sex_age = td_text
            elif not sex_age and re.fullmatch(r"[牡牝セ騸]\d{1,2}", td_text):
                sex_age = td_text

            # 斤量セル: "Txt_C" クラスまたは数値パターン
            if any(c in ("Txt_C",) for c in td_classes) and not weight_carry:
                val = _safe_float(td_text)
                if val and 40.0 <= val <= 65.0:
                    weight_carry = val

            # 騎手: /jockey/ リンクを含むセル
            jockey_link = td.find("a", href=re.compile(r"/jockey/"))
            if jockey_link and not jockey_id:
                jockey_name = jockey_link.get_text(strip=True)
                m = re.search(r"/jockey/(\w+)", jockey_link.get("href", ""))
                if m:
                    jockey_id = m.group(1).rstrip("/")

            # 調教師: /trainer/ リンクを含むセル
            trainer_link = td.find("a", href=re.compile(r"/trainer/"))
            if trainer_link and not trainer_id:
                trainer_name = trainer_link.get_text(strip=True)
                m = re.search(r"/trainer/(\w+)", trainer_link.get("href", ""))
                if m:
                    trainer_id = m.group(1).rstrip("/")

            # 馬体重セル: "XXX(+Y)" パターン
            if re.search(r"\d{3}\([+-]?\d+\)", td_text) and horse_weight is None:
                horse_weight = td_text

            # オッズセル: "Popular" / "Odds" クラス
            if any("Odds" in c or "Popular" in c for c in td_classes):
                # 人気順
                pop_val = _safe_int(td_text)
                if pop_val is not None and 1 <= pop_val <= 30:
                    popularity = pop_val
                # オッズ値
                odds_val = _safe_float(td_text)
                if odds_val is not None and odds_val > 1.0 and morning_odds is None:
                    morning_odds = odds_val

        # 斤量がまだ取れていない場合のフォールバック
        if not weight_carry:
            for td in tds:
                val = _safe_float(td.get_text(strip=True))
                if val and 48.0 <= val <= 62.0:
                    weight_carry = val
                    break

        entry_id = f"{race_id}_{horse_number:02d}"

        entries.append(UpcomingHorseEntry(
            entry_id=entry_id,
            race_id=race_id,
            frame_number=frame_number,
            horse_number=horse_number,
            horse_name=horse_name,
            horse_id=horse_id,
            sex_age=sex_age,
            weight_carry=weight_carry,
            jockey_name=jockey_name,
            jockey_id=jockey_id,
            trainer_name=trainer_name,
            trainer_id=trainer_id,
            horse_weight=horse_weight,
            morning_odds=morning_odds,
            popularity=popularity,
        ))

    return race_info, entries


# ---------------------------------------------------------------------------
# 2. 馬の戦績ページパーサー
# ---------------------------------------------------------------------------

def parse_horse_history_page(
    html: str, horse_id: str, horse_name: str
) -> Optional[HorseHistory]:
    """
    馬の成績ページ (db.netkeiba.com/horse/{horse_id}/) をパースし、
    HorseHistory を返す。

    取得内容:
      - 通算成績 (total_runs, wins, places, shows)
      - 直近5走の詳細 (recent_results)
      - 馬場別成績 (surface_stats)
      - 距離別成績 (distance_stats)
      - 競馬場別成績 (venue_stats)
      - 脚質判定 (running_style) ← 通過順位から算出

    HTML構造: テーブル class="db_h_race_results" に全レース結果行が並ぶ。
    """
    soup = BeautifulSoup(html, "lxml")

    # 成績テーブルを探す
    table = soup.find("table", class_="db_h_race_results")
    if table is None:
        # フォールバック: nk_tb_common を試行
        table = soup.find("table", class_="nk_tb_common")
    if table is None:
        return None

    tbody = table.find("tbody")
    if tbody is None:
        tbody = table

    rows = tbody.find_all("tr")
    if not rows:
        return None

    # 全走のデータを収集
    all_records: List[PastRaceRecord] = []

    # 統計用カウンター
    total_runs = 0
    wins = 0
    places = 0  # 2着
    shows = 0   # 3着

    # 馬場別・距離別・競馬場別の統計
    surface_counter: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"runs": 0, "wins": 0, "places": 0, "shows": 0}
    )
    distance_counter: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"runs": 0, "wins": 0, "places": 0, "shows": 0}
    )
    venue_counter: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"runs": 0, "wins": 0, "places": 0, "shows": 0}
    )

    # 脚質判定用の通過順リスト
    corner_positions_list: List[Optional[str]] = []

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 15:
            continue

        # 各セルのテキストを取得
        try:
            # 日付 (0列目)
            date_text = tds[0].get_text(strip=True)
            # YYYY/MM/DD 形式をパース
            date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
            if not date_match:
                continue
            race_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

            # 競馬場 (1列目)
            venue_text = tds[1].get_text(strip=True)
            # "1東京" -> "東京", "3中山" -> "中山" のように数字を除去
            venue = re.sub(r"^\d+", "", venue_text).strip()

            # 天候 (2列目)
            weather = tds[2].get_text(strip=True)

            # レース番号 (3列目) - 使用しないが存在確認
            # R = tds[3].get_text(strip=True)

            # レース名 (4列目)
            race_name_text = tds[4].get_text(strip=True)

            # 頭数 (5列目) - 使用しないが存在確認

            # 枠番 (6列目)
            # frame = _safe_int(tds[6].get_text(strip=True))

            # 馬番 (7列目)
            horse_number_val = _safe_int(tds[7].get_text(strip=True))
            if horse_number_val is None:
                horse_number_val = 0

            # 単勝オッズ (8列目)
            odds_val = _safe_float(tds[8].get_text(strip=True))

            # 人気 (9列目)
            pop_val = _safe_int(tds[9].get_text(strip=True))

            # 着順 (10列目)
            order_text = tds[10].get_text(strip=True)
            result_order = _safe_int(order_text)

            # 騎手 (11列目) - 名前のみ取得
            # jockey = tds[11].get_text(strip=True)

            # 斤量 (12列目)
            weight_carry = _safe_float(tds[12].get_text(strip=True))

            # コース (13列目): 芝/ダ + 距離
            course_text = tds[13].get_text(strip=True)
            surface = "芝"
            if "ダ" in course_text:
                surface = "ダート"
            elif "障" in course_text:
                surface = "障害"
            dist_match = re.search(r"(\d{3,5})", course_text)
            distance = int(dist_match.group(1)) if dist_match else 0

            # 馬場状態 (14列目)
            track_condition = tds[14].get_text(strip=True)

            # タイム (15列目 or 以降)
            time_str: Optional[str] = None
            if len(tds) > 15:
                time_text = tds[15].get_text(strip=True)
                if re.match(r"\d+:\d+\.\d+", time_text):
                    time_str = time_text

            # 着差 (16列目) - 使用しない

            # 上り3F (17列目)
            last_3f: Optional[float] = None
            if len(tds) > 17:
                last_3f = _safe_float(tds[17].get_text(strip=True))

            # ペース (20列目付近)
            pace: Optional[str] = None
            if len(tds) > 20:
                pace_text = tds[20].get_text(strip=True)
                if pace_text and re.search(r"\d", pace_text):
                    pace = pace_text

            # 通過順 (19列目付近)
            position_at_corners: Optional[str] = None
            if len(tds) > 19:
                pos_text = tds[19].get_text(strip=True)
                if re.match(r"\d+-", pos_text):
                    position_at_corners = pos_text

            # 馬体重 (22列目付近)
            horse_weight: Optional[str] = None
            if len(tds) > 23:
                hw_text = tds[23].get_text(strip=True)
                if re.search(r"\d{3}", hw_text):
                    horse_weight = hw_text

            # レースクラス判定（レース名ベース）
            race_class = _parse_race_class("", race_name_text)

        except (IndexError, AttributeError):
            # パースエラーは静かにスキップ
            continue

        # レコード作成
        record = PastRaceRecord(
            race_date=race_date,
            venue=venue,
            race_name=race_name_text,
            surface=surface,
            distance=distance,
            weather=weather,
            track_condition=track_condition,
            horse_number=horse_number_val,
            result_order=result_order,
            time_str=time_str,
            last_3f=last_3f,
            odds=odds_val,
            popularity=pop_val,
            weight_carry=weight_carry,
            horse_weight=horse_weight,
            pace=pace,
            position_at_corners=position_at_corners,
            race_class=race_class,
        )
        all_records.append(record)

        # --- 統計の集計 ---
        total_runs += 1
        is_win = result_order == 1
        is_place = result_order == 2
        is_show = result_order == 3

        if is_win:
            wins += 1
        if is_place:
            places += 1
        if is_show:
            shows += 1

        # 馬場別
        if surface in ("芝", "ダート"):
            surface_counter[surface]["runs"] += 1
            if is_win:
                surface_counter[surface]["wins"] += 1
            if is_place:
                surface_counter[surface]["places"] += 1
            if is_show:
                surface_counter[surface]["shows"] += 1

        # 距離別
        if distance > 0:
            dist_key = _distance_range_key(distance)
            distance_counter[dist_key]["runs"] += 1
            if is_win:
                distance_counter[dist_key]["wins"] += 1
            if is_place:
                distance_counter[dist_key]["places"] += 1
            if is_show:
                distance_counter[dist_key]["shows"] += 1

        # 競馬場別
        if venue and venue != "不明":
            venue_counter[venue]["runs"] += 1
            if is_win:
                venue_counter[venue]["wins"] += 1
            if is_place:
                venue_counter[venue]["places"] += 1
            if is_show:
                venue_counter[venue]["shows"] += 1

        # 脚質判定用
        corner_positions_list.append(position_at_corners)

    if total_runs == 0:
        return None

    # 直近5走を取得（all_records はページ上の順番＝新しい順）
    recent_results = all_records[:5]

    # 脚質判定（直近5走の通過順を使用）
    recent_corners = corner_positions_list[:5]
    running_style = _classify_running_style(recent_corners)

    return HorseHistory(
        horse_id=horse_id,
        horse_name=horse_name,
        total_runs=total_runs,
        wins=wins,
        places=places,
        shows=shows,
        recent_results=recent_results,
        surface_stats=dict(surface_counter),
        distance_stats=dict(distance_counter),
        venue_stats=dict(venue_counter),
        running_style=running_style,
    )


# ---------------------------------------------------------------------------
# 3. 騎手成績ページパーサー
# ---------------------------------------------------------------------------

def parse_jockey_stats_page(
    html: str, jockey_id: str, jockey_name: str
) -> Optional[JockeyStats]:
    """
    騎手成績ページをパースし、JockeyStats を返す。

    対象: db.netkeiba.com/jockey/result/{jockey_id}/ もしくは
          db.netkeiba.com/jockey/{jockey_id}/

    年間成績テーブルから本年の成績を抽出する。
    テーブル形式: 年度 | 1着 | 2着 | 3着 | 着外 | ... | 勝率 | 連対率 | 複勝率

    競馬場別成績テーブルからも統計を取得する。
    """
    soup = BeautifulSoup(html, "lxml")

    year_runs = 0
    year_wins = 0
    year_win_rate = 0.0
    year_place_rate = 0.0
    year_show_rate = 0.0
    venue_stats: Dict[str, Dict[str, float]] = {}

    # --- 年度別成績テーブル ---
    # 複数テーブルを走査し、年度別成績を探す
    tables = soup.find_all("table", class_="nk_tb_common")
    if not tables:
        tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        # ヘッダー確認: 1行目に「年度」「1着」等が含まれるかチェック
        header_text = rows[0].get_text()
        if "年度" not in header_text and "1着" not in header_text:
            continue

        # 最新年度の行を探す（通常は2行目以降で最初の行が最新年度）
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 7:
                continue

            # 年度セルの確認（数字4桁 or "合計" を期待）
            year_text = cells[0].get_text(strip=True)

            # 合計行はスキップして年度データを使う
            if "合計" in year_text or "累計" in year_text:
                continue

            # 本年度または最新年度の行を使用
            year_match = re.match(r"(\d{4})", year_text)
            if not year_match:
                continue

            try:
                # 1着, 2着, 3着, 着外 を取得
                wins_val = _safe_int(cells[1].get_text(strip=True)) or 0
                places_val = _safe_int(cells[2].get_text(strip=True)) or 0
                shows_val = _safe_int(cells[3].get_text(strip=True)) or 0
                unplaced_val = _safe_int(cells[4].get_text(strip=True)) or 0

                total = wins_val + places_val + shows_val + unplaced_val

                if total > 0:
                    year_runs = total
                    year_wins = wins_val
                    year_win_rate = round(wins_val / total, 4)
                    year_place_rate = round((wins_val + places_val) / total, 4)
                    year_show_rate = round(
                        (wins_val + places_val + shows_val) / total, 4
                    )
                    # 最新年度が見つかったら終了
                    break
            except (IndexError, ValueError):
                continue

        # 年度データが見つかったらテーブルループを抜ける
        if year_runs > 0:
            break

    # --- 競馬場別成績テーブル ---
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        header_text = rows[0].get_text()
        # 競馬場別テーブルの判定: 「場所」「競馬場」等を含む
        if "場" not in header_text:
            continue
        # 年度別テーブルは除外
        if "年度" in header_text:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 5:
                continue

            venue_name = cells[0].get_text(strip=True)
            # 有効な競馬場名かチェック
            if venue_name not in VENUE_CODE_MAP.values():
                continue

            try:
                v_wins = _safe_int(cells[1].get_text(strip=True)) or 0
                v_places = _safe_int(cells[2].get_text(strip=True)) or 0
                v_shows = _safe_int(cells[3].get_text(strip=True)) or 0
                v_unplaced = _safe_int(cells[4].get_text(strip=True)) or 0
                v_total = v_wins + v_places + v_shows + v_unplaced

                if v_total > 0:
                    venue_stats[venue_name] = {
                        "runs": float(v_total),
                        "win_rate": round(v_wins / v_total, 4),
                        "show_rate": round(
                            (v_wins + v_places + v_shows) / v_total, 4
                        ),
                    }
            except (IndexError, ValueError):
                continue

        # 競馬場別データが見つかったら終了
        if venue_stats:
            break

    # データが全く取れなかった場合
    if year_runs == 0 and not venue_stats:
        return None

    return JockeyStats(
        jockey_id=jockey_id,
        jockey_name=jockey_name,
        year_runs=year_runs,
        year_wins=year_wins,
        year_win_rate=year_win_rate,
        year_place_rate=year_place_rate,
        year_show_rate=year_show_rate,
        venue_stats=venue_stats,
    )


# ---------------------------------------------------------------------------
# 4. 調教師成績ページパーサー
# ---------------------------------------------------------------------------

def parse_trainer_stats_page(
    html: str, trainer_id: str, trainer_name: str
) -> Optional[TrainerStats]:
    """
    調教師成績ページをパースし、TrainerStats を返す。

    対象: db.netkeiba.com/trainer/result/{trainer_id}/ もしくは
          db.netkeiba.com/trainer/{trainer_id}/

    年度別成績テーブルから本年の成績を抽出する。
    """
    soup = BeautifulSoup(html, "lxml")

    year_runs = 0
    year_wins = 0
    year_win_rate = 0.0
    year_show_rate = 0.0

    # 成績テーブルを走査
    tables = soup.find_all("table", class_="nk_tb_common")
    if not tables:
        tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        header_text = rows[0].get_text()
        if "年度" not in header_text and "1着" not in header_text:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 5:
                continue

            year_text = cells[0].get_text(strip=True)
            if "合計" in year_text or "累計" in year_text:
                continue

            year_match = re.match(r"(\d{4})", year_text)
            if not year_match:
                continue

            try:
                wins_val = _safe_int(cells[1].get_text(strip=True)) or 0
                places_val = _safe_int(cells[2].get_text(strip=True)) or 0
                shows_val = _safe_int(cells[3].get_text(strip=True)) or 0
                unplaced_val = _safe_int(cells[4].get_text(strip=True)) or 0

                total = wins_val + places_val + shows_val + unplaced_val
                if total > 0:
                    year_runs = total
                    year_wins = wins_val
                    year_win_rate = round(wins_val / total, 4)
                    year_show_rate = round(
                        (wins_val + places_val + shows_val) / total, 4
                    )
                    break
            except (IndexError, ValueError):
                continue

        if year_runs > 0:
            break

    if year_runs == 0:
        return None

    return TrainerStats(
        trainer_id=trainer_id,
        trainer_name=trainer_name,
        year_runs=year_runs,
        year_wins=year_wins,
        year_win_rate=year_win_rate,
        year_show_rate=year_show_rate,
    )


# ---------------------------------------------------------------------------
# 5. レースカレンダーページパーサー
# ---------------------------------------------------------------------------

def parse_race_calendar_page(html: str) -> List[str]:
    """
    レース一覧ページ (race.netkeiba.com/top/race_list.html?kaisai_date=YYYYMMDD)
    をパースし、その日の全 race_id のリストを返す。

    中央競馬（JRA）のレースのみ抽出する（venue_code が 01-10）。

    HTML構造:
      - レースリンクが "shutuba.html?race_id=XXXXXXXXXXXX" 形式
      - または "/race/XXXXXXXXXXXX/" 形式
    """
    soup = BeautifulSoup(html, "lxml")
    race_ids: List[str] = []
    seen: set = set()

    # パターン1: shutuba.html?race_id=XXXXXXXXXXXX
    links = soup.find_all(
        "a", href=re.compile(r"race_id=(\d{12})")
    )
    for link in links:
        href = link.get("href", "")
        m = re.search(r"race_id=(\d{12})", href)
        if m:
            rid = m.group(1)
            venue_code = rid[4:6]
            if venue_code in VENUE_CODE_MAP and rid not in seen:
                race_ids.append(rid)
                seen.add(rid)

    # パターン2: /race/XXXXXXXXXXXX/ 形式（フォールバック）
    if not race_ids:
        links = soup.find_all(
            "a", href=re.compile(r"/race/(\d{12})")
        )
        for link in links:
            href = link.get("href", "")
            m = re.search(r"/race/(\d{12})", href)
            if m:
                rid = m.group(1)
                venue_code = rid[4:6]
                if venue_code in VENUE_CODE_MAP and rid not in seen:
                    race_ids.append(rid)
                    seen.add(rid)

    # パターン3: data-race-id 属性（JavaScript レンダリングの場合）
    if not race_ids:
        elements = soup.find_all(attrs={"data-race-id": re.compile(r"\d{12}")})
        for elem in elements:
            rid = elem.get("data-race-id", "")
            if len(rid) == 12 and rid.isdigit():
                venue_code = rid[4:6]
                if venue_code in VENUE_CODE_MAP and rid not in seen:
                    race_ids.append(rid)
                    seen.add(rid)

    return race_ids


# ---------------------------------------------------------------------------
# 6. 単勝オッズページパーサー
# ---------------------------------------------------------------------------

def parse_win_odds_page(html: str, race_id: str) -> Dict[int, float]:
    """
    単勝オッズページをパースし、馬番 -> 単勝オッズ の辞書を返す。

    対象:
      - race.netkeiba.com/odds/index.html?type=b1&race_id=XXX
      - または出馬表ページ内のオッズ情報

    HTML構造:
      - テーブル内に「馬番」と「オッズ」の列がある
      - または "Odds" クラスの要素に馬番とオッズがペアで並ぶ
    """
    soup = BeautifulSoup(html, "lxml")
    odds_dict: Dict[int, float] = {}

    # パターン1: オッズテーブル（class="W31" や "nk_tb_common" 等）
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 2:
                continue

            # 馬番とオッズのペアを探す
            horse_num = None
            odds_val = None

            for td in tds:
                td_text = td.get_text(strip=True)
                td_classes = td.get("class", [])

                # 馬番セル: "Umaban" クラスまたは数値1-18
                if any("Umaban" in c or "umaban" in c for c in td_classes):
                    horse_num = _safe_int(td_text)
                elif any("Odds" in c or "odds" in c for c in td_classes):
                    odds_val = _safe_float(td_text)

            # クラス属性で取れなかった場合、位置ベースで取得
            if horse_num is None and odds_val is None and len(tds) >= 2:
                # 最初のセルが馬番、2番目以降にオッズを期待
                first_val = _safe_int(tds[0].get_text(strip=True))
                if first_val is not None and 1 <= first_val <= 18:
                    horse_num = first_val
                    # 残りのセルからオッズ値を探す
                    for td in tds[1:]:
                        val = _safe_float(td.get_text(strip=True))
                        if val is not None and val >= 1.0:
                            odds_val = val
                            break

            if horse_num is not None and odds_val is not None:
                odds_dict[horse_num] = odds_val

    # パターン2: リスト形式のオッズ（OddsList 等）
    if not odds_dict:
        odds_items = soup.find_all("div", class_=re.compile(r"(?i)odds"))
        for item in odds_items:
            # 馬番を取得
            num_elem = item.find(class_=re.compile(r"(?i)umaban|num"))
            odds_elem = item.find(class_=re.compile(r"(?i)odds_val|value"))

            if num_elem and odds_elem:
                horse_num = _safe_int(num_elem.get_text(strip=True))
                odds_val = _safe_float(odds_elem.get_text(strip=True))
                if horse_num is not None and odds_val is not None:
                    odds_dict[horse_num] = odds_val

    # パターン3: JSON/script タグ内のオッズデータ
    if not odds_dict:
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string
            if not script_text:
                continue
            # "odds":{"1":"2.3","2":"5.6",...} のようなパターン
            odds_matches = re.findall(
                r'"(\d{1,2})"\s*:\s*"(\d+\.?\d*)"', script_text
            )
            for num_str, odds_str in odds_matches:
                num = _safe_int(num_str)
                val = _safe_float(odds_str)
                if num is not None and val is not None and 1 <= num <= 18:
                    odds_dict[num] = val
            if odds_dict:
                break

    return odds_dict
