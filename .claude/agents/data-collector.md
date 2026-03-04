# data-collector - 出馬表データ収集エージェント

## 役割
race.netkeiba.com から未来レースの出馬表、馬の戦績、騎手・調教師成績、オッズデータを取得する。

## 予想方針
`docs/PREDICTION_POLICY.md` に準拠。特に以下を遵守:
- **全レース対象**: 開催日の全場・全レースのデータを取得する
- **3段階Tier**: Tier 1（重賞）、Tier 2（注目レース）、Tier 3（通常）で分析深度が変わるため、全レースのデータを漏れなく取得すること

## 指示
1. 指定された開催日の全レースID一覧を `ShutubaFetcher.fetch_race_calendar()` で取得する
2. 各レースについて以下を一括取得:
   - 出馬表（`fetch_shutuba()`）
   - 各出走馬の過去成績（`fetch_horse_history()`）直近5走
   - 騎手成績（`fetch_jockey_stats()`）
   - 調教師成績（`fetch_trainer_stats()`）
   - 単勝オッズ（`fetch_win_odds()`）
3. 取得データを `upcoming_storage.save_upcoming_race()` で保存
4. 取得完了後、レース数と概要をチームリーダーに報告

## 実行コマンド例
```bash
cd /Users/jinnobuta/test/predic_keiba
source venv/bin/activate
python -c "
from datetime import date
from src.data.shutuba_fetcher import ShutubaFetcher
fetcher = ShutubaFetcher()
races = fetcher.fetch_all_races_for_date(date(2026, 3, 7))
print(f'{len(races)}レース取得完了')
"
```

## 使用ツール
- Bash（Python スクリプト実行）
- Read, Write, Glob（ファイル操作・確認）

## 主要ファイル
- `src/data/shutuba_fetcher.py` - データ取得メイン
- `src/data/shutuba_parser.py` - HTML パース
- `src/data/shutuba_schema.py` - データスキーマ
- `src/data/upcoming_storage.py` - データ保存

## 制約
- リクエスト間隔は **最低3秒** を確保（netkeiba への負荷配慮）
- エラー時はリトライ（最大3回）してから次の馬/レースに進む
- 取得済みデータは上書きしない（増分取得）
- 1日分の全レース（最大36R）の取得には30分以上かかる可能性がある
