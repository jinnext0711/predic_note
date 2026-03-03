"""Note記事を生成するモジュール。

レース分析データと馬券戦略データを受け取り、
Note投稿用のMarkdown記事テキストを組み立てる。
"""

from __future__ import annotations

from typing import List


class NoteArticleWriter:
    """レース分析・戦略データからNote記事を生成するクラス。"""

    # 波乱度ラベルに対応する絵文字
    _VOLATILITY_EMOJI = {
        "堅い": "",
        "上位拮抗": "",
        "波乱含み": "",
        "大波乱": "",
    }

    # 自信度に対応する星表示
    _CONFIDENCE_STARS = {
        "A": "A",
        "B": "B",
        "C": "C",
        "D": "D",
    }

    # 重賞/特別戦かどうかを判定するキーワード
    _MAIN_RACE_KEYWORDS = (
        "G1", "G2", "G3", "GI", "GII", "GIII",
        "重賞", "特別", "ステークス", "S", "賞",
    )

    # ---------------------------------------------------------------
    # パブリックメソッド
    # ---------------------------------------------------------------

    def compose_article(
        self,
        race_date: str,
        analyses: List[dict],
        strategies: List[dict],
    ) -> str:
        """記事全体を組み立てて返す。

        Parameters
        ----------
        race_date : str
            開催日 (例: "2026-03-01")
        analyses : List[dict]
            レースごとの分析データリスト
        strategies : List[dict]
            レースごとの馬券戦略データリスト

        Returns
        -------
        str
            Note投稿用Markdown記事テキスト
        """
        sections: list[str] = []

        # ヘッダー
        sections.append(self._write_header(race_date, analyses))

        # メインレース(重賞/特別戦)と一般レースを分離
        main_races: list[tuple[dict, dict]] = []
        regular_races: list[tuple[dict, dict]] = []

        for analysis, strategy in zip(analyses, strategies):
            if self._is_main_race(analysis):
                main_races.append((analysis, strategy))
            else:
                regular_races.append((analysis, strategy))

        # メインレースを先に詳細分析で出力
        if main_races:
            sections.append("---")
            sections.append("## 本日のメインレース")
            sections.append("")
            for analysis, strategy in main_races:
                sections.append(self._write_race_section(analysis, strategy))

        # 一般レース
        if regular_races:
            sections.append("---")
            sections.append("## その他の注目レース")
            sections.append("")
            for analysis, strategy in regular_races:
                sections.append(self._write_race_section(analysis, strategy))

        # フッター
        sections.append(self._write_footer(strategies))

        return "\n".join(sections)

    # ---------------------------------------------------------------
    # プライベートメソッド - 各セクション生成
    # ---------------------------------------------------------------

    def _write_header(self, race_date: str, analyses: List[dict]) -> str:
        """タイトルとオープニングセクションを生成する。"""
        # 日付をフォーマット (例: "2026年3月1日")
        formatted_date = self._format_date(race_date)

        # メインレース名をリストアップ
        main_race_names = [
            a.get("race_name", "")
            for a in analyses
            if self._is_main_race(a)
        ]

        lines: list[str] = []
        lines.append(f"# {formatted_date} 競馬予想・全レース分析")
        lines.append("")

        if main_race_names:
            title_races = "／".join(main_race_names)
            lines.append(f"**本日の注目: {title_races}**")
            lines.append("")

        lines.append(
            "データ分析×期待値の観点から、本日の全レースを徹底解剖します。"
            "各馬の能力指数・調子・展開適性を総合評価し、"
            "回収率を意識した買い目を提案します。"
        )
        lines.append("")

        # サマリーテーブル
        lines.append(f"> 対象: **{len(analyses)}レース** ｜ "
                      f"メイン: **{len(main_race_names)}鞍**")
        lines.append("")

        return "\n".join(lines)

    def _write_race_section(self, analysis: dict, strategy: dict) -> str:
        """1レース分のフルセクションを生成する。"""
        lines: list[str] = []

        # セクション1: 対象レース
        race_name = analysis.get("race_name", "不明")
        venue = analysis.get("venue", "")
        surface = analysis.get("surface", "")
        distance = analysis.get("distance", "")
        grade = analysis.get("grade", "")
        num_horses = analysis.get("num_horses", "")

        lines.append(f"### {race_name}")
        lines.append("")
        condition_parts = [
            p for p in [venue, surface, f"{distance}m" if distance else "",
                        grade, f"{num_horses}頭" if num_horses else ""]
            if p
        ]
        if condition_parts:
            lines.append(f"**{' / '.join(condition_parts)}**")
            lines.append("")

        # セクション2: コース傾向
        lines.append(self._write_course_analysis(analysis))

        # セクション3: レース診断
        lines.append(self._write_race_diagnosis(analysis))

        # セクション4: 全馬評価テーブル
        lines.append(self._write_horse_evaluation_table(analysis))

        # セクション5: 最終結論
        lines.append(self._write_final_conclusion(analysis))

        # セクション6: 買い目
        lines.append(self._write_betting_recommendations(strategy))

        lines.append("")
        return "\n".join(lines)

    def _write_course_analysis(self, analysis: dict) -> str:
        """コース傾向・データ分析セクションを生成する。"""
        lines: list[str] = []
        lines.append("#### コース傾向・データ分析")
        lines.append("")

        # 有利な枠
        favorable_post = analysis.get("favorable_post", "")
        if favorable_post:
            lines.append(f"- **有利な枠**: {favorable_post}")

        # 有利な脚質
        favorable_style = analysis.get("favorable_style", "")
        if favorable_style:
            lines.append(f"- **有利な脚質**: {favorable_style}")

        # 馬場状態
        track_condition = analysis.get("track_condition", "")
        if track_condition:
            lines.append(f"- **馬場状態**: {track_condition}")

        # コース特徴(自由テキスト)
        course_note = analysis.get("course_note", "")
        if course_note:
            lines.append(f"- {course_note}")

        # データがまったく無い場合のフォールバック
        if not any([favorable_post, favorable_style,
                     track_condition, course_note]):
            lines.append("- データなし")

        lines.append("")
        return "\n".join(lines)

    def _write_race_diagnosis(self, analysis: dict) -> str:
        """レース診断セクション(波乱度・自信度・見解)を生成する。"""
        lines: list[str] = []
        lines.append("#### レース診断")
        lines.append("")

        volatility = analysis.get("volatility", "")
        confidence = analysis.get("confidence", "")
        comment = analysis.get("diagnosis_comment", "")

        # 波乱度
        if volatility:
            emoji = self._VOLATILITY_EMOJI.get(volatility, "")
            vol_display = f"{emoji} {volatility}" if emoji else volatility
            lines.append(f"- **波乱度**: {vol_display}")

        # 自信度
        if confidence:
            stars = self._CONFIDENCE_STARS.get(confidence, confidence)
            # 自信度Aなら星マーク付与
            star_mark = " ⭐" if confidence == "A" else ""
            lines.append(f"- **自信度**: {stars}{star_mark}")

        # 見解
        if comment:
            lines.append(f"- **見解**: {comment}")

        lines.append("")
        return "\n".join(lines)

    def _write_horse_evaluation_table(self, analysis: dict) -> str:
        """全馬評価のMarkdownテーブルを生成する。"""
        lines: list[str] = []
        lines.append("#### 全馬評価")
        lines.append("")

        horses = analysis.get("horses", [])
        if not horses:
            lines.append("評価データなし")
            lines.append("")
            return "\n".join(lines)

        # テーブルヘッダー
        lines.append(
            "| 馬番 | 馬名 | 能力 | 調子 | 騎手 | 展開 | 血統 | 厩舎 | 総合指数 |"
        )
        lines.append(
            "|:----:|:-----|:----:|:----:|:----:|:----:|:----:|:----:|:--------:|"
        )

        # 総合指数でソート(降順)して出力
        sorted_horses = sorted(
            horses,
            key=lambda h: h.get("total_score", 0),
            reverse=True,
        )

        for horse in sorted_horses:
            number = horse.get("number", "")
            name = horse.get("name", "")
            ability = horse.get("ability", "")
            condition = horse.get("condition", "")
            jockey = horse.get("jockey", "")
            pace_fit = horse.get("pace_fit", "")
            bloodline = horse.get("bloodline", "")
            stable = horse.get("stable", "")
            total = horse.get("total_score", "")

            lines.append(
                f"| {number} | {name} | {ability} | {condition} "
                f"| {jockey} | {pace_fit} | {bloodline} | {stable} | **{total}** |"
            )

        lines.append("")
        return "\n".join(lines)

    def _write_final_conclusion(self, analysis: dict) -> str:
        """最終結論・期待値ギャップ分析セクションを生成する。"""
        lines: list[str] = []
        lines.append("#### 最終結論・期待値ギャップ分析")
        lines.append("")

        # 印と評価理由
        selections = analysis.get("selections", [])
        if selections:
            lines.append("**予想印**")
            lines.append("")
            for sel in selections:
                mark = sel.get("mark", "")
                name = sel.get("name", "")
                number = sel.get("number", "")
                reason = sel.get("reason", "")
                # 本命にはホットマーク
                hot = " 🔥" if mark == "◎" else ""
                lines.append(f"- **{mark} {number} {name}**{hot}: {reason}")
            lines.append("")

        # 血統・厩舎補正
        bloodline_notes = analysis.get("bloodline_stable_notes", "")
        if bloodline_notes:
            lines.append(f"**血統・厩舎による特注補正**: {bloodline_notes}")
            lines.append("")

        # 期待値ギャップ
        value_gaps = analysis.get("value_gaps", [])
        if value_gaps:
            lines.append("**人気との期待値ギャップ**")
            lines.append("")
            for gap in value_gaps:
                horse_name = gap.get("name", "")
                popularity = gap.get("popularity", "")
                assessment = gap.get("assessment", "")
                lines.append(f"- {horse_name}（{popularity}番人気）: {assessment}")
            lines.append("")

        # 危険な人気馬
        danger_horses = analysis.get("danger_horses", [])
        if danger_horses:
            lines.append("**危険な人気馬（消し）**")
            lines.append("")
            for dh in danger_horses:
                name = dh.get("name", "")
                reason = dh.get("reason", "")
                lines.append(f"- ×{name}: {reason}")
            lines.append("")

        return "\n".join(lines)

    def _write_betting_recommendations(self, strategy: dict) -> str:
        """推奨買い目セクションを生成する。"""
        lines: list[str] = []
        lines.append("#### 推奨買い目")
        lines.append("")

        # 推奨(勝ちを意識) - アグレッシブ
        aggressive = strategy.get("aggressive", [])
        if aggressive:
            lines.append("**【攻めの馬券】** 回収率重視・勝ちを意識")
            lines.append("")
            for bet in aggressive:
                bet_type = bet.get("type", "")
                detail = bet.get("detail", "")
                amount = bet.get("amount", "")
                amount_str = f"（{amount}円）" if amount else ""
                lines.append(f"- {bet_type}: {detail}{amount_str}")
            lines.append("")

        # 最も効率的な戦略 - コンサバティブ
        conservative = strategy.get("conservative", [])
        if conservative:
            lines.append("**【守りの馬券】** 的中率重視・ガミらない")
            lines.append("")
            for bet in conservative:
                bet_type = bet.get("type", "")
                detail = bet.get("detail", "")
                amount = bet.get("amount", "")
                amount_str = f"（{amount}円）" if amount else ""
                lines.append(f"- {bet_type}: {detail}{amount_str}")
            lines.append("")

        # 合計投資額
        total_investment = strategy.get("total_investment", "")
        if total_investment:
            lines.append(f"> このレースの推奨投資額: **{total_investment}円**")
            lines.append("")

        return "\n".join(lines)

    def _write_footer(self, strategies: List[dict]) -> str:
        """記事フッター(全体サマリー)を生成する。"""
        lines: list[str] = []
        lines.append("---")
        lines.append("")
        lines.append("## 本日の投資サマリー")
        lines.append("")

        # 全レースの合計投資額を計算
        total = 0
        race_count = 0
        for strategy in strategies:
            inv = strategy.get("total_investment", 0)
            if inv:
                try:
                    total += int(inv)
                    race_count += 1
                except (ValueError, TypeError):
                    pass

        if total > 0:
            lines.append(f"- **対象レース数**: {race_count}鞍")
            lines.append(f"- **合計投資額**: {total:,}円")
            lines.append("")

        lines.append(
            "> 馬券は期待値の積み重ね。"
            "1日単位ではなく、月単位・年単位での回収率を意識しましょう。"
        )
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "*本記事はデータ分析に基づく予想です。"
            "馬券の購入は自己責任でお願いいたします。*"
        )
        lines.append("")

        return "\n".join(lines)

    # ---------------------------------------------------------------
    # ユーティリティ
    # ---------------------------------------------------------------

    def _is_main_race(self, analysis: dict) -> bool:
        """重賞・特別戦かどうかを判定する。"""
        race_name = analysis.get("race_name", "")
        grade = analysis.get("grade", "")
        is_main = analysis.get("is_main_race", False)

        # 明示フラグがあればそれを優先
        if is_main:
            return True

        # レース名やグレードにメインレースのキーワードが含まれるかチェック
        combined = f"{race_name}{grade}"
        return any(kw in combined for kw in self._MAIN_RACE_KEYWORDS)

    @staticmethod
    def _format_date(date_str: str) -> str:
        """日付文字列を日本語フォーマットに変換する。

        Parameters
        ----------
        date_str : str
            "YYYY-MM-DD" 形式の日付

        Returns
        -------
        str
            "YYYY年M月D日" 形式
        """
        try:
            parts = date_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            return f"{year}年{month}月{day}日"
        except (IndexError, ValueError):
            # パースできない場合はそのまま返す
            return date_str
