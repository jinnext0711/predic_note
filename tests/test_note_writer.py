"""
Note記事生成 (note_writer.py) のテスト。

NoteArticleWriter の compose_article を中心に、
各セクション（ヘッダー、コース傾向、全馬評価テーブル等）の
出力内容を検証する。
"""
import pytest

from article.note_writer import NoteArticleWriter


# ---------------------------------------------------------------------------
# ヘルパー関数: サンプルデータ生成
# ---------------------------------------------------------------------------


def _make_horse_data(
    number: int,
    name: str,
    total_score: float = 70.0,
    ability: str = "B",
    condition: str = "B",
    jockey: str = "C",
    pace_fit: str = "B",
    bloodline: str = "C",
    stable: str = "C",
) -> dict:
    """テスト用の馬評価データ dict を生成する。"""
    return {
        "number": number,
        "name": name,
        "total_score": total_score,
        "ability": ability,
        "condition": condition,
        "jockey": jockey,
        "pace_fit": pace_fit,
        "bloodline": bloodline,
        "stable": stable,
    }


def _make_analysis(
    race_name: str = "テストステークス",
    venue: str = "中山",
    surface: str = "芝",
    distance: int = 2000,
    grade: str = "G3",
    is_main: bool = False,
    volatility: str = "上位拮抗",
    confidence: str = "B",
    horses: list = None,
    selections: list = None,
) -> dict:
    """テスト用の分析データ dict を生成する。"""
    if horses is None:
        horses = [
            _make_horse_data(1, "テスト馬A", 85.0, "A", "A", "B", "A", "B", "B"),
            _make_horse_data(2, "テスト馬B", 72.0, "B", "B", "C", "B", "C", "C"),
            _make_horse_data(3, "テスト馬C", 60.0, "C", "C", "C", "C", "C", "C"),
        ]
    if selections is None:
        selections = [
            {"mark": "◎", "number": 1, "name": "テスト馬A", "reason": "能力最上位"},
            {"mark": "○", "number": 2, "name": "テスト馬B", "reason": "安定した成績"},
            {"mark": "▲", "number": 3, "name": "テスト馬C", "reason": "穴馬として注目"},
        ]
    return {
        "race_name": race_name,
        "venue": venue,
        "surface": surface,
        "distance": distance,
        "grade": grade,
        "num_horses": len(horses),
        "is_main_race": is_main,
        "volatility": volatility,
        "confidence": confidence,
        "diagnosis_comment": "テスト見解コメント",
        "favorable_post": "内枠有利",
        "favorable_style": "先行有利",
        "track_condition": "良",
        "course_note": "小回りコースで先行有利",
        "horses": horses,
        "selections": selections,
        "value_gaps": [
            {"name": "テスト馬C", "popularity": "5", "assessment": "人気以上の実力"},
        ],
        "danger_horses": [
            {"name": "テスト馬D", "reason": "距離適性に疑問"},
        ],
    }


def _make_strategy(
    total_investment: int = 5000,
    aggressive: list = None,
    conservative: list = None,
) -> dict:
    """テスト用の馬券戦略データ dict を生成する。"""
    if aggressive is None:
        aggressive = [
            {"type": "三連単", "detail": "1>2>3", "amount": 300},
            {"type": "馬単", "detail": "1>2", "amount": 500},
        ]
    if conservative is None:
        conservative = [
            {"type": "ワイド", "detail": "1-2", "amount": 500},
            {"type": "複勝", "detail": "1", "amount": 1000},
        ]
    return {
        "total_investment": total_investment,
        "aggressive": aggressive,
        "conservative": conservative,
    }


# ===========================================================================
# 基本テスト
# ===========================================================================


class TestComposeArticleBasic:
    """compose_article の基本テスト。"""

    @pytest.fixture
    def writer(self) -> NoteArticleWriter:
        """NoteArticleWriter のインスタンス。"""
        return NoteArticleWriter()

    def test_produces_non_empty_output(self, writer):
        """記事が空でないこと。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert len(article) > 0

    def test_output_is_string(self, writer):
        """記事が文字列であること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert isinstance(article, str)

    def test_header_includes_date(self, writer):
        """ヘッダーに日付が含まれること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-03-15", analyses, strategies)
        assert "2025年3月15日" in article

    def test_header_includes_race_count(self, writer):
        """ヘッダーにレース数が含まれること。"""
        analyses = [_make_analysis(), _make_analysis(race_name="レース2")]
        strategies = [_make_strategy(), _make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert "2レース" in article


# ===========================================================================
# セクション存在確認テスト
# ===========================================================================


class TestSectionsPresent:
    """記事の各セクションが存在することの確認テスト。"""

    @pytest.fixture
    def article(self) -> str:
        """テスト用の完全な記事を生成する。"""
        writer = NoteArticleWriter()
        analyses = [_make_analysis(is_main=True)]
        strategies = [_make_strategy()]
        return writer.compose_article("2025-01-01", analyses, strategies)

    def test_race_name_section(self, article):
        """レース名セクションが存在すること。"""
        assert "テストステークス" in article

    def test_course_analysis_section(self, article):
        """コース傾向セクションが存在すること。"""
        assert "コース傾向" in article

    def test_race_diagnosis_section(self, article):
        """レース診断セクションが存在すること。"""
        assert "レース診断" in article

    def test_horse_evaluation_section(self, article):
        """全馬評価セクションが存在すること。"""
        assert "全馬評価" in article

    def test_final_conclusion_section(self, article):
        """最終結論セクションが存在すること。"""
        assert "最終結論" in article

    def test_betting_recommendations_section(self, article):
        """推奨買い目セクションが存在すること。"""
        assert "推奨買い目" in article

    def test_investment_summary_section(self, article):
        """投資サマリーセクションが存在すること。"""
        assert "投資サマリー" in article

    def test_disclaimer_present(self, article):
        """免責事項が含まれること。"""
        assert "自己責任" in article


# ===========================================================================
# Markdownテーブルのテスト
# ===========================================================================


class TestMarkdownTable:
    """全馬評価テーブルのフォーマットテスト。"""

    @pytest.fixture
    def article(self) -> str:
        writer = NoteArticleWriter()
        analyses = [_make_analysis(is_main=True)]
        strategies = [_make_strategy()]
        return writer.compose_article("2025-01-01", analyses, strategies)

    def test_table_header_present(self, article):
        """テーブルヘッダーが含まれること。"""
        assert "| 馬番 | 馬名 |" in article

    def test_table_separator_present(self, article):
        """テーブルのセパレータ行が含まれること。"""
        assert "|:----:|" in article

    def test_table_contains_horse_data(self, article):
        """テーブルに馬データが含まれること。"""
        assert "テスト馬A" in article
        assert "テスト馬B" in article

    def test_table_rows_have_pipe_separators(self, article):
        """テーブル行がパイプ区切りであること。"""
        # 各行の先頭と末尾が | であること
        lines = article.split("\n")
        table_lines = [l for l in lines if l.strip().startswith("|") and "馬番" not in l and "----" not in l and l.strip().endswith("|")]
        assert len(table_lines) > 0

    def test_no_horses_shows_fallback(self):
        """馬データなしの場合にフォールバックメッセージが表示されること。"""
        writer = NoteArticleWriter()
        analysis = _make_analysis(horses=[])
        strategy = _make_strategy()
        article = writer.compose_article("2025-01-01", [analysis], [strategy])
        assert "評価データなし" in article


# ===========================================================================
# ヘッダー・フッターのテスト
# ===========================================================================


class TestHeaderFooter:
    """ヘッダーとフッターのテスト。"""

    @pytest.fixture
    def writer(self) -> NoteArticleWriter:
        return NoteArticleWriter()

    def test_header_includes_markdown_h1(self, writer):
        """ヘッダーに H1 タイトルが含まれること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert article.startswith("# ")

    def test_footer_includes_disclaimer(self, writer):
        """フッターに免責事項が含まれること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert "自己責任" in article

    def test_footer_includes_total_investment(self, writer):
        """フッターに合計投資額が含まれること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy(total_investment=8000)]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert "8,000円" in article

    def test_footer_period_emphasis(self, writer):
        """フッターに期待値メッセージが含まれること。"""
        analyses = [_make_analysis()]
        strategies = [_make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert "期待値" in article


# ===========================================================================
# メインレース判定のテスト
# ===========================================================================


class TestMainRaceDetection:
    """メインレース（重賞・特別戦）判定のテスト。"""

    @pytest.fixture
    def writer(self) -> NoteArticleWriter:
        return NoteArticleWriter()

    def test_explicit_main_flag(self, writer):
        """is_main_race フラグが True の場合にメインレースと判定されること。"""
        assert writer._is_main_race({"is_main_race": True, "race_name": "普通のレース", "grade": ""})

    def test_g1_keyword(self, writer):
        """レース名に G1 を含む場合にメインレースと判定されること。"""
        assert writer._is_main_race({"race_name": "日本ダービー", "grade": "G1"})

    def test_stakes_keyword(self, writer):
        """レース名にステークスを含む場合にメインレースと判定されること。"""
        assert writer._is_main_race({"race_name": "京成杯ステークス", "grade": ""})

    def test_regular_race(self, writer):
        """一般レースの場合にメインレースと判定されないこと。"""
        assert not writer._is_main_race({"race_name": "3歳未勝利", "grade": ""})

    def test_main_races_appear_first(self, writer):
        """重賞レース（Tier 1）が注目レース（Tier 2）より先に出力されること。"""
        analyses = [
            _make_analysis(race_name="3歳未勝利", is_main=False, grade=""),
            _make_analysis(race_name="テストG1", is_main=True, grade="G1"),
        ]
        strategies = [_make_strategy(), _make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        # 重賞レースセクション（Tier 1）が注目レースセクション（Tier 2）より先に出現すること
        tier1_pos = article.find("重賞レース（フル分析）")
        tier2_pos = article.find("注目レース（詳細分析）")
        assert tier1_pos != -1, "重賞レースセクションが見つからない"
        assert tier2_pos != -1, "注目レースセクションが見つからない"
        assert tier1_pos < tier2_pos


# ===========================================================================
# 日付フォーマットのテスト
# ===========================================================================


class TestFormatDate:
    """日付フォーマットのテスト。"""

    @pytest.mark.parametrize("input_date, expected", [
        ("2025-01-01", "2025年1月1日"),
        ("2025-12-31", "2025年12月31日"),
        ("2026-03-15", "2026年3月15日"),
    ])
    def test_valid_dates(self, input_date, expected):
        """有効な日付が正しくフォーマットされること。"""
        assert NoteArticleWriter._format_date(input_date) == expected

    def test_invalid_date_returns_original(self):
        """不正な日付文字列はそのまま返されること。"""
        assert NoteArticleWriter._format_date("invalid") == "invalid"
        assert NoteArticleWriter._format_date("") == ""


# ===========================================================================
# コース傾向・レース診断の内容テスト
# ===========================================================================


class TestCourseAndDiagnosis:
    """コース傾向・レース診断の内容テスト。"""

    @pytest.fixture
    def writer(self) -> NoteArticleWriter:
        return NoteArticleWriter()

    def test_favorable_post_displayed(self, writer):
        """有利な枠が表示されること。"""
        analysis = _make_analysis()
        strategy = _make_strategy()
        article = writer.compose_article("2025-01-01", [analysis], [strategy])
        assert "内枠有利" in article

    def test_favorable_style_displayed(self, writer):
        """有利な脚質が表示されること。"""
        analysis = _make_analysis()
        strategy = _make_strategy()
        article = writer.compose_article("2025-01-01", [analysis], [strategy])
        assert "先行有利" in article

    def test_volatility_displayed(self, writer):
        """波乱度が表示されること。"""
        analysis = _make_analysis(volatility="大波乱")
        strategy = _make_strategy()
        article = writer.compose_article("2025-01-01", [analysis], [strategy])
        assert "大波乱" in article

    def test_confidence_displayed(self, writer):
        """自信度が表示されること。"""
        analysis = _make_analysis(confidence="A")
        strategy = _make_strategy()
        article = writer.compose_article("2025-01-01", [analysis], [strategy])
        assert "A" in article


# ===========================================================================
# 複数レースの記事テスト
# ===========================================================================


class TestMultipleRaces:
    """複数レースの記事生成テスト。"""

    @pytest.fixture
    def writer(self) -> NoteArticleWriter:
        return NoteArticleWriter()

    def test_multiple_races_all_included(self, writer):
        """複数レースの情報がすべて含まれること。"""
        analyses = [
            _make_analysis(race_name="レースA"),
            _make_analysis(race_name="レースB"),
            _make_analysis(race_name="レースC"),
        ]
        strategies = [_make_strategy(), _make_strategy(), _make_strategy()]
        article = writer.compose_article("2025-01-01", analyses, strategies)
        assert "レースA" in article
        assert "レースB" in article
        assert "レースC" in article

    def test_empty_analyses_no_error(self, writer):
        """分析データが空でもエラーにならないこと。"""
        article = writer.compose_article("2025-01-01", [], [])
        assert isinstance(article, str)
        assert len(article) > 0
