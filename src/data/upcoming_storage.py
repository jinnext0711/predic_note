"""
未来レース（出馬表）データの保存・読み込み（JSON を data/ 以下に保存）。

対象:
- 出馬表データ (shutuba.json)
- 分析結果 (analysis.json)
- 買い目戦略 (strategy.json)
- 記事テキスト (data/articles/)
"""
import json
from pathlib import Path
from typing import List, Optional

from .shutuba_schema import UpcomingRaceWithEntries


# ---------------------------------------------------------------------------
# ディレクトリヘルパー
# ---------------------------------------------------------------------------

def _upcoming_dir(base: Path = None) -> Path:
    """未来レースデータの保存先ディレクトリ。プロジェクトルートの data/upcoming/ を想定。"""
    if base is None:
        base = Path(__file__).resolve().parent.parent.parent  # predic_keiba ルート
    d = base / "data" / "upcoming"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _articles_dir(base: Path = None) -> Path:
    """記事テキストの保存先ディレクトリ。プロジェクトルートの data/articles/ を想定。"""
    if base is None:
        base = Path(__file__).resolve().parent.parent.parent  # predic_keiba ルート
    d = base / "data" / "articles"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# 出馬表データ (shutuba.json)
# ---------------------------------------------------------------------------

def save_upcoming_race(race_data: UpcomingRaceWithEntries, base_path: Path = None) -> Path:
    """未来レースの出馬表データを JSON で保存する。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_data.race_id.replace("/", "_").replace("\\", "_")
    race_dir = data_dir / safe_id
    race_dir.mkdir(parents=True, exist_ok=True)
    path = race_dir / "shutuba.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(race_data.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_upcoming_race(race_id: str, base_path: Path = None) -> Optional[UpcomingRaceWithEntries]:
    """保存済みの出馬表データを読み込む。存在しなければ None を返す。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    path = data_dir / safe_id / "shutuba.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UpcomingRaceWithEntries.from_dict(data)


# ---------------------------------------------------------------------------
# 分析結果 (analysis.json)
# ---------------------------------------------------------------------------

def save_analysis(race_id: str, analysis: dict, base_path: Path = None) -> Path:
    """レースの分析結果を JSON で保存する。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    race_dir = data_dir / safe_id
    race_dir.mkdir(parents=True, exist_ok=True)
    path = race_dir / "analysis.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return path


def load_analysis(race_id: str, base_path: Path = None) -> Optional[dict]:
    """保存済みの分析結果を読み込む。存在しなければ None を返す。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    path = data_dir / safe_id / "analysis.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 買い目戦略 (strategy.json)
# ---------------------------------------------------------------------------

def save_strategy(race_id: str, strategy: dict, base_path: Path = None) -> Path:
    """レースの買い目戦略を JSON で保存する。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    race_dir = data_dir / safe_id
    race_dir.mkdir(parents=True, exist_ok=True)
    path = race_dir / "strategy.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)
    return path


def load_strategy(race_id: str, base_path: Path = None) -> Optional[dict]:
    """保存済みの買い目戦略を読み込む。存在しなければ None を返す。"""
    data_dir = _upcoming_dir(base_path)
    safe_id = race_id.replace("/", "_").replace("\\", "_")
    path = data_dir / safe_id / "strategy.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 記事テキスト (data/articles/{race_date}_article.md)
# ---------------------------------------------------------------------------

def save_article(article_text: str, race_date: str, base_path: Path = None) -> Path:
    """記事テキストを Markdown ファイルとして保存する。"""
    data_dir = _articles_dir(base_path)
    safe_date = race_date.replace("/", "_").replace("\\", "_")
    path = data_dir / f"{safe_date}_article.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(article_text)
    return path


def load_article(race_date: str, base_path: Path = None) -> Optional[str]:
    """保存済みの記事テキストを読み込む。存在しなければ None を返す。"""
    data_dir = _articles_dir(base_path)
    safe_date = race_date.replace("/", "_").replace("\\", "_")
    path = data_dir / f"{safe_date}_article.md"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 一覧取得
# ---------------------------------------------------------------------------

def list_upcoming_race_ids(base_path: Path = None) -> List[str]:
    """保存済みの未来レース race_id 一覧を返す（ディレクトリ名から復元）。"""
    data_dir = _upcoming_dir(base_path)
    race_ids = []
    for child in sorted(data_dir.iterdir()):
        if child.is_dir() and (child / "shutuba.json").exists():
            race_ids.append(child.name)
    return race_ids
