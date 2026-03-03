"""
netkeiba.com レース結果ページ・レース一覧ページのHTMLパーサー。

レース結果ページ (db.netkeiba.com/race/{race_id}/) から
Race + List[HorseEntry] を抽出する。
"""
import re
from datetime import date
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

from .schema import Race, HorseEntry


# 競馬場コードと名称の対応
VENUE_CODE_MAP = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}

# クラスの正規化マッピング
CLASS_NORMALIZE = {
    "新馬": "新馬",
    "未勝利": "未勝利",
    "1勝クラス": "1勝",
    "1勝": "1勝",
    "2勝クラス": "2勝",
    "2勝": "2勝",
    "3勝クラス": "3勝",
    "3勝": "3勝",
    "オープン": "オープン",
    "OP": "オープン",
    "(L)": "オープン",
    "リステッド": "オープン",
    "(G1)": "G1",
    "G1": "G1",
    "(G2)": "G2",
    "G2": "G2",
    "(G3)": "G3",
    "G3": "G3",
    "(GI)": "G1",
    "GI": "G1",
    "(GII)": "G2",
    "GII": "G2",
    "(GIII)": "G3",
    "GIII": "G3",
}


def _extract_venue_from_race_id(race_id: str) -> str:
    """race_idから競馬場名を取得。race_id形式: YYYY{venue_code}{kai}{day}{race_num}"""
    if len(race_id) >= 6:
        venue_code = race_id[4:6]
        return VENUE_CODE_MAP.get(venue_code, "不明")
    return "不明"


def _parse_distance_and_surface(course_text: str) -> Tuple[int, str]:
    """
    コース情報テキストから距離とコース種別を抽出。
    例: '芝左2400m / 天候 : 晴 / ...' -> (2400, '芝')
    """
    surface = "芝"
    if "ダ" in course_text:
        surface = "ダート"
    elif "障" in course_text:
        surface = "障害"

    m = re.search(r"(\d{3,5})\s*m", course_text)
    distance = int(m.group(1)) if m else 0
    return distance, surface


def _parse_race_class(info_text: str, race_name: str = "") -> str:
    """
    レース情報テキストからクラスを判定。
    info_text例: '3歳オープン  (国際) 牡・牝(指)(馬齢)'
    race_name例: '第91回東京優駿(GI)'
    """
    # グレードレース判定（レース名から）
    if race_name:
        for pattern, cls in [
            (r"\(GI\)|\(G1\)", "G1"),
            (r"\(GII\)|\(G2\)", "G2"),
            (r"\(GIII\)|\(G3\)", "G3"),
        ]:
            if re.search(pattern, race_name):
                return cls

    # info_textからクラス判定
    combined = info_text + " " + race_name
    if "新馬" in combined:
        return "新馬"
    if "未勝利" in combined:
        return "未勝利"
    if "3勝" in combined:
        return "3勝"
    if "2勝" in combined:
        return "2勝"
    if "1勝" in combined:
        return "1勝"
    if "リステッド" in combined or "(L)" in combined:
        return "オープン"
    if "オープン" in combined or "OP" in combined:
        return "オープン"
    return "オープン"


def _parse_age_condition(info_text: str) -> str:
    """
    年齢条件を抽出。
    例: '2歳未勝利' -> '2歳', '3歳以上1勝クラス' -> '3歳以上', '4歳以上オープン' -> '4歳以上'
    """
    m = re.search(r"(\d歳(?:以上)?)", info_text)
    if m:
        return m.group(1)
    return "3歳以上"


def _parse_date(info_text: str) -> Optional[date]:
    """
    日付を抽出。
    例: '2024年05月26日 2回東京12日目 ...' -> date(2024, 5, 26)
    """
    m = re.search(r"(\d{4})年(\d{2})月(\d{2})日", info_text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def parse_race_result_page(html: str, race_id: str) -> Tuple[Optional[Race], List[HorseEntry]]:
    """
    レース結果ページのHTMLをパースし、Race と HorseEntry のリストを返す。

    取消・除外・中止の馬は result_order=None, final_odds=None で含める。
    """
    soup = BeautifulSoup(html, "lxml")

    # --- レース情報の抽出 ---
    # コース情報（芝/ダート・距離）
    racedata = soup.find("dl", class_="racedata")
    if not racedata:
        return None, []

    span = racedata.find("span")
    course_text = span.get_text() if span else ""
    distance, surface = _parse_distance_and_surface(course_text)

    # 障害レースはスキップ
    if surface == "障害":
        return None, []

    # レース名
    h1 = racedata.find("h1")
    race_name = h1.get_text(strip=True) if h1 else ""

    # 日付・クラス・年齢条件（smalltxt）
    smalltxt = soup.find("p", class_="smalltxt")
    info_text = smalltxt.get_text() if smalltxt else ""

    race_date = _parse_date(info_text)
    if race_date is None:
        return None, []

    race_class = _parse_race_class(info_text, race_name)
    age_condition = _parse_age_condition(info_text)

    # 競馬場はrace_idから取得（テキストからも取れるが、race_idの方が確実）
    venue = _extract_venue_from_race_id(race_id)

    race = Race(
        race_id=race_id,
        date=race_date,
        venue=venue,
        distance=distance,
        surface=surface,
        race_class=race_class,
        age_condition=age_condition,
        race_name=race_name,
    )

    # --- 出走馬情報の抽出 ---
    table = soup.find("table", class_="race_table_01")
    if not table:
        return race, []

    entries: List[HorseEntry] = []
    rows = table.find_all("tr")

    for row in rows[1:]:  # ヘッダー行をスキップ
        tds = row.find_all("td")
        if len(tds) < 15:
            continue

        # 着順（数値でない場合は取消・除外・中止など）
        order_text = tds[0].get_text(strip=True)
        result_order = None
        try:
            result_order = int(order_text)
        except (ValueError, TypeError):
            pass

        # 枠番・馬番
        try:
            frame_number = int(tds[1].get_text(strip=True))
        except (ValueError, TypeError):
            frame_number = 0
        try:
            horse_number = int(tds[2].get_text(strip=True))
        except (ValueError, TypeError):
            continue  # 馬番が取れない行はスキップ

        # 馬名
        horse_name = tds[3].get_text(strip=True)
        if not horse_name:
            continue

        # 斤量
        weight = None
        try:
            weight = float(tds[5].get_text(strip=True))
        except (ValueError, TypeError):
            pass

        # 単勝オッズ
        final_odds = None
        odds_text = tds[12].get_text(strip=True)
        try:
            final_odds = float(odds_text)
        except (ValueError, TypeError):
            pass  # '---' など（取消馬）

        entry_id = f"{race_id}_{horse_number:02d}"

        entries.append(HorseEntry(
            entry_id=entry_id,
            race_id=race_id,
            frame_number=frame_number,
            horse_number=horse_number,
            horse_name=horse_name,
            weight=weight,
            final_odds=final_odds,
            result_order=result_order,
        ))

    race.number_of_entries = len(entries)
    return race, entries


def parse_race_list_page(html: str) -> List[str]:
    """
    日付別レース一覧ページのHTMLをパースし、race_id のリストを返す。
    中央競馬（JRA）のレースのみ抽出する。
    """
    soup = BeautifulSoup(html, "lxml")
    race_ids: List[str] = []

    # レースリンクを探す（/race/{12桁数字}/ 形式）
    links = soup.find_all("a", href=re.compile(r"/race/(\d{12})/"))
    seen = set()
    for link in links:
        m = re.search(r"/race/(\d{12})/", link.get("href", ""))
        if m:
            rid = m.group(1)
            # 中央競馬のみ: venue_code が 01-10
            venue_code = rid[4:6]
            if venue_code in VENUE_CODE_MAP and rid not in seen:
                race_ids.append(rid)
                seen.add(rid)

    return race_ids
