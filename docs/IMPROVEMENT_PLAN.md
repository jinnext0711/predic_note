# predic_keiba 改善プラン

## 評価概要
- 評価日: 2026-03-03
- 評価エージェント: ui-reviewer, scenario-tester, backtest-evaluator
- 検出問題数: 46件（クリティカル6 / 重要10 / Nice-to-have 8 / 軽微22）

## クリティカル改善（即座対応）

### C1: 複勝オッズ近似の修正
- **ファイル**: `src/simulation.py:317`
- **問題**: 複勝オッズを単勝/3で近似しているが楽観的すぎる（実際は約1/2.6）
- **修正**: `pick.final_odds / 3.0` → `pick.final_odds / 2.6`
- **影響**: バックテスト結果の回収率が実態に近づく

### C2: 専門用語の初心者向け改善
- **ファイル**: `src/pages/create_logic.py` 全般、各ページのヘルプテキスト
- **問題**: Scope/Must/Prefer-Avoidが競馬初心者に不明
- **修正**:
  - 「Scope」→ 画面上は「対象レース条件」と表記
  - 「Must」→「必須条件（満たさない馬は対象外）」と表記
  - 「Prefer/Avoid」→「優先/回避条件」と表記
  - ウィザードのステップ名もこれに合わせる

### C3: ロジック作成完了→バックテストへの導線
- **ファイル**: `src/pages/create_logic.py:480` (_save_logic関数の末尾)
- **問題**: 保存後に「次はバックテスト」という導線がない
- **修正**: 保存成功時に「バックテスト画面でこのロジックを検証できます」のメッセージ表示

### C4: エラー表示の初心者向け改善
- **ファイル**: `src/pages/create_logic.py:491-494`, `my_logics.py`, `backtest.py`, `community.py`
- **問題**: traceback.format_exc()がそのまま表示される
- **修正**: 共通の例外ハンドラでユーザー向けメッセージに変換。tracebackはloggerへ

### C5: フォワード成績フォームの改善
- **ファイル**: `src/pages/community.py:167`
- **問題**: レースID形式の説明がない
- **修正**:
  - placeholder を `"例: 202501010101（年4桁+開催コード8桁）"` に
  - 複勝選択時に「3着以内が的中」と明記

### C6: バックテスト結果の診断機能
- **ファイル**: `src/pages/backtest.py:148-154`
- **問題**: 「条件を見直してみましょう」だけでは行動に繋がらない
- **修正**: 回収率×的中率の組み合わせで具体的なアドバイスを出す
  - 低的中率(< 15%): 「Must条件が厳しすぎるかもしれません。条件を緩めてみましょう」
  - 的中率OK/回収率低: 「オッズ帯の設定を見直すと改善する可能性があります」
  - 高的中率/回収率低: 「単勝への切り替えやオッズ帯下限の引上げを検討してみましょう」
  - 回収率>=110%: 「好成績です！フォワード成績で実運用の検証を始めましょう」

## 重要改善（次フェーズ）

### I1: バックテスト出力指標の拡充
- `src/simulation.py` のrun_backtest戻り値に追加:
  - 平均利益（1試行あたり）
  - Profit Factor（総利益/総損失）
  - 最大連勝数

### I2: サンプルサイズ信頼度表示
- `src/pages/backtest.py` に信頼度バナー:
  - trials < 50: 「⚠ サンプル数が少ないため信頼度が低い」
  - trials < 200: 「参考値としてご覧ください」

### I3: ロジックメタデータ拡充
- `src/logic_store.py` にフィールド追加: description, created_at
- `src/pages/community.py` で表示

### I4: Must条件カテゴリ追加 ✅ 実装済み
- `src/data/schema.py` HorseEntryに: horse_sex, days_since_last_race を追加
- `src/models/must.py` MUST_CATEGORIES_LISTに「馬の性別」「前走間隔（日数）」を追加
- `src/simulation.py` _get_entry_value マッピングに追加

### I5: マイロジック→バックテストのクイックリンク
- `src/pages/my_logics.py` に「バックテスト実行」ボタン

### I6: 編集モードの明確化
- `src/pages/create_logic.py` で「新規作成」「既存編集」をタブで明確に分離

### I7: バックテストvsフォワード並列表示
- `src/pages/my_logics.py` にバックテスト成績タブ追加

### I8: 演算子の日本語表記
- `src/models/must.py` MUST_OPERATORSを「以下(<=)」形式に

### I9: community.pyの結果表示統一
- backtest.pyと同じメトリクス（DD、連敗数）を表示

### I10: delta_colorロジック修正
- `src/pages/backtest.py:138` の判定を適切に

## Nice-to-have（将来）
- Must ブロックの色分け・バッジ表示
- 複数ロジック成績比較画面
- 月別・競馬場別クロスタビュー
- メトリクスフォント拡大
- モバイル対応
- 年別推移グラフに標準偏差表示
