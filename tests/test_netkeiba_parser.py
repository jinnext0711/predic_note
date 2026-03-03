"""
netkeiba_parser のテスト。

実際のHTMLに似たフィクスチャーを使い、パースロジックをテストする。
"""
import pytest
from datetime import date

from src.data.netkeiba_parser import (
    parse_race_result_page,
    parse_race_list_page,
    _extract_venue_from_race_id,
    _parse_distance_and_surface,
    _parse_race_class,
    _parse_age_condition,
    _parse_date,
)


# --- ユーティリティ関数のテスト ---


class TestExtractVenue:
    def test_tokyo(self):
        assert _extract_venue_from_race_id("202405021211") == "東京"

    def test_nakayama(self):
        assert _extract_venue_from_race_id("202406010101") == "中山"

    def test_hanshin(self):
        assert _extract_venue_from_race_id("202409010101") == "阪神"

    def test_sapporo(self):
        assert _extract_venue_from_race_id("202401010101") == "札幌"

    def test_unknown(self):
        assert _extract_venue_from_race_id("202499010101") == "不明"

    def test_short_id(self):
        assert _extract_venue_from_race_id("2024") == "不明"


class TestParseDistanceAndSurface:
    def test_turf(self):
        assert _parse_distance_and_surface("芝左2400m / 天候 : 晴") == (2400, "芝")

    def test_dirt(self):
        assert _parse_distance_and_surface("ダ右1200m / 天候 : 曇") == (1200, "ダート")

    def test_obstacle(self):
        assert _parse_distance_and_surface("障芝3000m") == (3000, "障害")

    def test_no_distance(self):
        d, s = _parse_distance_and_surface("芝左 / 天候 : 晴")
        assert s == "芝"
        assert d == 0


class TestParseRaceClass:
    def test_g1_from_name(self):
        assert _parse_race_class("3歳オープン", "第91回東京優駿(GI)") == "G1"

    def test_g2_from_name(self):
        assert _parse_race_class("3歳以上オープン", "毎日王冠(GII)") == "G2"

    def test_g3_from_name(self):
        assert _parse_race_class("3歳以上オープン", "京成杯(GIII)") == "G3"

    def test_maiden(self):
        assert _parse_race_class("3歳未勝利") == "未勝利"

    def test_newcomer(self):
        assert _parse_race_class("2歳新馬") == "新馬"

    def test_one_win(self):
        assert _parse_race_class("3歳以上1勝クラス") == "1勝"

    def test_two_win(self):
        assert _parse_race_class("4歳以上2勝クラス") == "2勝"

    def test_three_win(self):
        assert _parse_race_class("4歳以上3勝クラス") == "3勝"

    def test_open(self):
        assert _parse_race_class("3歳以上オープン") == "オープン"

    def test_listed(self):
        assert _parse_race_class("3歳以上オープン", "ジュニアC(L)") == "オープン"


class TestParseAgeCondition:
    def test_two_year(self):
        assert _parse_age_condition("2歳新馬") == "2歳"

    def test_three_year(self):
        assert _parse_age_condition("3歳オープン") == "3歳"

    def test_three_and_above(self):
        assert _parse_age_condition("3歳以上1勝クラス") == "3歳以上"

    def test_four_and_above(self):
        assert _parse_age_condition("4歳以上オープン") == "4歳以上"

    def test_fallback(self):
        assert _parse_age_condition("") == "3歳以上"


class TestParseDate:
    def test_normal(self):
        assert _parse_date("2024年05月26日 2回東京12日目") == date(2024, 5, 26)

    def test_no_match(self):
        assert _parse_date("no date here") is None


# --- レース結果ページパースのテスト ---


# テスト用の最小限HTMLフィクスチャー
RACE_RESULT_HTML = """
<html>
<body>
<div class="data_intro">
 <dl class="racedata fc">
  <dt>11 R</dt>
  <dd>
   <h1>テストレース(GI)</h1>
   <p><span>芝左2000m / 天候 : 晴 / 芝 : 良 / 発走 : 15:40</span></p>
  </dd>
 </dl>
 <p class="smalltxt">2024年06月01日 1回東京1日目 3歳オープン  (国際) 牡・牝(指)(馬齢)</p>
</div>
<table class="race_table_01 nk_tb_common" summary="レース結果">
<tr class="header">
<th>着順</th><th>枠番</th><th>馬番</th><th>馬名</th><th>性齢</th>
<th>斤量</th><th>騎手</th><th>タイム</th><th>着差</th><th>ﾀｲﾑ指数</th>
<th>通過</th><th>上り</th><th>単勝</th><th>人気</th><th>馬体重</th>
</tr>
<tr>
<td class="txt_r">1</td>
<td class="w3ml">1</td>
<td class="txt_r">1</td>
<td class="txt_l"><a href="/horse/2021100001/">テスト馬A</a></td>
<td class="txt_c">牡3</td>
<td class="txt_c">57</td>
<td class="txt_l"><a href="/jockey/result/recent/00001/">テスト騎手</a></td>
<td class="txt_r">2:00.0</td>
<td class="txt_c"></td>
<td class="speed_index bml">**</td>
<td>1-1-1-1</td>
<td class="r3ml txt_c">34.0</td>
<td class="txt_r">3.5</td>
<td class="bml">1</td>
<td>480(+2)</td>
</tr>
<tr>
<td class="txt_r">2</td>
<td class="w3ml">2</td>
<td class="txt_r">3</td>
<td class="txt_l"><a href="/horse/2021100002/">テスト馬B</a></td>
<td class="txt_c">牡3</td>
<td class="txt_c">55</td>
<td class="txt_l"><a href="/jockey/result/recent/00002/">テスト騎手B</a></td>
<td class="txt_r">2:00.5</td>
<td class="txt_c">3</td>
<td class="speed_index bml">**</td>
<td>3-3-2-2</td>
<td class="r3ml txt_c">34.5</td>
<td class="txt_r">5.0</td>
<td class="bml">2</td>
<td>460(-4)</td>
</tr>
<tr>
<td class="txt_r">取</td>
<td class="w3ml">3</td>
<td class="txt_r">5</td>
<td class="txt_l"><a href="/horse/2021100003/">テスト馬C</a></td>
<td class="txt_c">牝3</td>
<td class="txt_c">55</td>
<td class="txt_l"><a href="/jockey/result/recent/00003/">テスト騎手C</a></td>
<td class="txt_r"></td>
<td class="txt_c"></td>
<td class="speed_index bml"></td>
<td></td>
<td class="r3ml txt_c"></td>
<td class="txt_r">---</td>
<td class="bml"></td>
<td></td>
</tr>
</table>
</body>
</html>
"""


class TestParseRaceResultPage:
    def test_race_info(self):
        race, entries = parse_race_result_page(RACE_RESULT_HTML, "202405010111")
        assert race is not None
        assert race.race_id == "202405010111"
        assert race.date == date(2024, 6, 1)
        assert race.venue == "東京"
        assert race.distance == 2000
        assert race.surface == "芝"
        assert race.race_class == "G1"
        assert race.age_condition == "3歳"
        assert race.race_name == "テストレース(GI)"

    def test_entry_count(self):
        race, entries = parse_race_result_page(RACE_RESULT_HTML, "202405010111")
        assert len(entries) == 3
        assert race.number_of_entries == 3

    def test_first_place(self):
        _, entries = parse_race_result_page(RACE_RESULT_HTML, "202405010111")
        first = entries[0]
        assert first.horse_name == "テスト馬A"
        assert first.horse_number == 1
        assert first.frame_number == 1
        assert first.result_order == 1
        assert first.final_odds == 3.5
        assert first.weight == 57.0
        assert first.entry_id == "202405010111_01"

    def test_second_place(self):
        _, entries = parse_race_result_page(RACE_RESULT_HTML, "202405010111")
        second = entries[1]
        assert second.horse_name == "テスト馬B"
        assert second.horse_number == 3
        assert second.result_order == 2
        assert second.final_odds == 5.0
        assert second.weight == 55.0

    def test_cancelled_horse(self):
        """取消馬は result_order=None, final_odds=None"""
        _, entries = parse_race_result_page(RACE_RESULT_HTML, "202405010111")
        cancelled = entries[2]
        assert cancelled.horse_name == "テスト馬C"
        assert cancelled.result_order is None
        assert cancelled.final_odds is None

    def test_no_table(self):
        """テーブルがない場合"""
        html = '<html><body><dl class="racedata"><span>芝2000m</span></dl><p class="smalltxt">2024年01月01日 テスト</p></body></html>'
        race, entries = parse_race_result_page(html, "test")
        # racedataはあるがtableがない
        assert entries == []

    def test_no_racedata(self):
        """racedataがない場合"""
        html = "<html><body></body></html>"
        race, entries = parse_race_result_page(html, "test")
        assert race is None
        assert entries == []

    def test_obstacle_race_skipped(self):
        """障害レースはスキップされる"""
        html = """
        <html><body>
        <dl class="racedata"><dd><h1>テスト</h1><p><span>障芝3000m</span></p></dd></dl>
        <p class="smalltxt">2024年01月01日 テスト 3歳以上オープン</p>
        </body></html>
        """
        race, entries = parse_race_result_page(html, "test")
        assert race is None


# --- レース一覧ページパースのテスト ---


RACE_LIST_HTML = """
<html>
<body>
<div class="race_list fc">
 <dl class="race_top_hold_list">
  <dt>中山</dt>
  <dd>
   <dl class="race_top_data_info fc">
    <dt>1R</dt>
    <dd><a href="/race/202406010101/">3歳未勝利</a></dd>
   </dl>
   <dl class="race_top_data_info fc">
    <dt>2R</dt>
    <dd><a href="/race/202406010102/">3歳未勝利</a></dd>
   </dl>
  </dd>
 </dl>
 <dl class="race_top_hold_list">
  <dt>京都</dt>
  <dd>
   <dl class="race_top_data_info fc">
    <dt>1R</dt>
    <dd><a href="/race/202408010101/">2歳新馬</a></dd>
   </dl>
  </dd>
 </dl>
 <!-- 地方競馬（スキップ対象） -->
 <dl class="race_top_hold_list">
  <dt>園田</dt>
  <dd>
   <dl class="race_top_data_info fc">
    <dt>1R</dt>
    <dd><a href="/race/202455010101/">地方レース</a></dd>
   </dl>
  </dd>
 </dl>
</div>
</body>
</html>
"""


class TestParseRaceListPage:
    def test_extracts_jra_races(self):
        race_ids = parse_race_list_page(RACE_LIST_HTML)
        assert "202406010101" in race_ids
        assert "202406010102" in race_ids
        assert "202408010101" in race_ids

    def test_excludes_nar_races(self):
        """地方競馬（venue_code 55）はスキップ"""
        race_ids = parse_race_list_page(RACE_LIST_HTML)
        assert "202455010101" not in race_ids

    def test_count(self):
        race_ids = parse_race_list_page(RACE_LIST_HTML)
        assert len(race_ids) == 3

    def test_no_duplicates(self):
        """重複リンクがあっても1つだけ"""
        html = """
        <html><body>
        <a href="/race/202406010101/">Link1</a>
        <a href="/race/202406010101/">Link2</a>
        </body></html>
        """
        race_ids = parse_race_list_page(html)
        assert len(race_ids) == 1

    def test_empty_page(self):
        race_ids = parse_race_list_page("<html><body></body></html>")
        assert race_ids == []
