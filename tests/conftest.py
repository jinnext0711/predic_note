"""
テスト共通設定。src をインポートパスに追加。
"""
import sys
from pathlib import Path

# src ディレクトリをパスに追加
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
