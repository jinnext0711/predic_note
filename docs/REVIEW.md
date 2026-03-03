# コードレビュー記録

## 対象: タスク 1.1, 1.2, 1.3, 2.1 の実装

---

### 指摘事項と対応

| # | 区分 | 内容 | 対応 |
|---|------|------|------|
| 1 | バグ | `save_races` が毎回全件上書き。増分取得で既存レースが消える | `merge=True` で既存を読み込み race_id でマージしてから保存。デフォルトは True。 |
| 2 | 堅牢性 | `logic_store.load_all` が JSON 破損で例外 | `try/except (json.JSONDecodeError, OSError)` で [] を返すよう変更済み。 |
| 3 | 型 | `RaceDataFetcher.fetch_races` の venue 等が `str = None` | `Optional[str] = None` に変更済み。 |
| 4 | 仕様 | スキーマ `from_dict` の必須キーが無いと KeyError | ドキュメントで明記（今回のスキーマは必須前提のためコード変更なし）。 |

---

### 確認済み（問題なし）

- `HorseEntry.from_dict`: weight/final_odds が 0 のときも正しく 0.0 になる
- `merge_odds_into_entries`: オッズ未設定時は既存 e.final_odds を維持
- `RaceScope.to_dict/from_dict`: リスト項目の保存・復元が正しい
- `update_entries_odds`: entry_id 単位でオッズをマージして保存
- パス解決: `storage` / `logic_store` の `__file__` からプロジェクトルートを算出しており、Streamlit 実行時も想定どおり

---

### 今後の改善候補

- `load_races` / `load_entries` の JSON 破損時に例外ではなくログ＋空リストを返す
- 実データ用 Fetcher 実装時にオッズ・日付のバリデーションを追加
- 単体テストの追加（pytest）
