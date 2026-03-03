#!/usr/bin/env python3
"""
レース・馬データ取得パイプラインの実行。

netkeiba.com から実データを取得し、data/ に保存する。
増分取得対応: 取得済みレースはスキップ。

例:
  cd predic_keiba && python -m src.data.run_fetch
  cd predic_keiba && python -m src.data.run_fetch --months 1
  cd predic_keiba && python -m src.data.run_fetch --months 24 --split-monthly
  cd predic_keiba && python -m src.data.run_fetch --start 2024-01-01 --end 2024-06-30 --split-monthly
  cd predic_keiba && python -m src.data.run_fetch --max-races 10
  cd predic_keiba && python -m src.data.run_fetch --compute-previous
"""
import argparse
import calendar
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

# プロジェクトルートを path に追加
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.data.pipeline import run_fetch_and_save, run_fetch_past_5_years
from src.data.netkeiba_fetcher import NetkeibaRaceDataFetcher
from src.data.previous_race import compute_previous_race_data


def _split_into_months(start: date, end: date) -> List[Tuple[date, date]]:
    """期間を月単位のチャンクに分割する。"""
    chunks = []
    current = start
    while current <= end:
        # この月の末日
        _, last_day = calendar.monthrange(current.year, current.month)
        month_end = date(current.year, current.month, last_day)
        chunk_end = min(month_end, end)
        chunks.append((current, chunk_end))
        # 翌月1日へ
        current = chunk_end + timedelta(days=1)
    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="netkeiba レースデータ取得",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 過去1ヶ月を一括取得
  python -m src.data.run_fetch --months 1

  # 過去2年分を月毎に分割取得（推奨）
  python -m src.data.run_fetch --months 24 --split-monthly

  # 特定期間を月毎に分割取得
  python -m src.data.run_fetch --start 2023-01-01 --end 2024-12-31 --split-monthly

  # 10レースだけ取得（動作確認用）
  python -m src.data.run_fetch --max-races 10

  # 前走データのみ再計算
  python -m src.data.run_fetch --compute-previous
""",
    )
    parser.add_argument("--start", type=str, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="終了日 (YYYY-MM-DD)")
    parser.add_argument("--months", type=int, help="過去Nヶ月分を取得")
    parser.add_argument("--split-monthly", action="store_true",
                        help="月毎に分割して取得（長期間の取得で推奨）")
    parser.add_argument("--max-races", type=int, help="取得レース数の上限")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="リクエスト間隔（秒、デフォルト3）")
    parser.add_argument("--no-skip", action="store_true",
                        help="取得済みレースもスキップしない")
    parser.add_argument("--compute-previous", action="store_true",
                        help="前走データを計算する")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="詳細ログ出力")
    args = parser.parse_args()

    # ログ設定
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 前走データ計算のみ
    if args.compute_previous:
        updated = compute_previous_race_data(base_path=_root)
        print(f"前走データ更新: {updated} レース")
        return 0

    # 期間の決定
    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.months:
        end_date = date.today()
        start_date = end_date - timedelta(days=args.months * 30)
    else:
        # デフォルト: 過去1ヶ月
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

    # 月分割チャンク生成
    if args.split_monthly:
        chunks = _split_into_months(start_date, end_date)
    else:
        chunks = [(start_date, end_date)]

    print(f"取得期間: {start_date} ～ {end_date}")
    print(f"リクエスト間隔: {args.interval}秒")
    if args.split_monthly:
        print(f"月分割: {len(chunks)} チャンク")

    total = 0
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        if args.split_monthly:
            print(f"\n--- [{i+1}/{len(chunks)}] {chunk_start} ～ {chunk_end} ---")

        fetcher = NetkeibaRaceDataFetcher(
            interval=args.interval,
            base_path=_root,
            skip_existing=not args.no_skip,
            max_races=args.max_races,
        )

        n = run_fetch_and_save(
            chunk_start, chunk_end,
            fetcher=fetcher,
            base_path=_root,
        )
        total += n
        print(f"保存: {n} レース（累計 {total}）")

    print(f"\n合計保存レース数: {total}")

    if total > 0:
        print("前走データを計算中...")
        updated = compute_previous_race_data(base_path=_root)
        print(f"前走データ更新: {updated} レース")

    return 0


if __name__ == "__main__":
    exit(main())
