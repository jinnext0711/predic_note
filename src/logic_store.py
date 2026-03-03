"""
ロジック記録の永続化（タスク 2.1, 2.2, 5.1, 5.2）。
Scope / Must / Prefer-Avoid / カスタム変数 / フォワード成績 を保存・読み込み。
ロジックのキーは (owner, name) の組み合わせで一意。
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any

from models.scope import RaceScope
from models.must import MustLogic, MustBlock
from models.prefer_avoid import PreferAvoidLogic
from models.custom_variable import CustomVariableSet
from models.forward_record import ForwardRecord, ForwardResult


def _store_path(base: Path = None) -> Path:
    if base is None:
        base = Path(__file__).resolve().parent.parent
    return base / "data" / "logics.json"


def _logic_key(rec: dict) -> str:
    """ロジックレコードからユニークキーを生成。owner+nameの組み合わせ。"""
    return f"{rec.get('owner', '')}::{rec.get('name', '')}"


def _build_index(logics: List[dict]) -> dict:
    """ロジックリストから (owner::name) → record の辞書を構築。"""
    index = {}
    for r in logics:
        index[_logic_key(r)] = r
    return index


def get_logic(name: str, owner: str = None, base_path: Path = None) -> Optional[dict]:
    """名前（とオーナー）でロジックを検索して返す。"""
    logics = load_all(base_path)
    for r in logics:
        if r.get("name") == name:
            if owner is not None and r.get("owner", "") != owner:
                continue
            return r
    return None


# 後方互換エイリアス
_get_by_name = get_logic


def save_scope(name: str, scope: RaceScope, owner: str = "", base_path: Path = None) -> Path:
    """
    ロジック名と Scope を保存する。既存の同名・同オーナーがいる場合は Scope のみ更新し Must/Prefer-Avoid は維持。
    戻り値: 保存先ファイルパス。
    """
    path = _store_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    logics = load_all(base_path)
    index = _build_index(logics)
    key = f"{owner}::{name}"
    existing = index.get(key, {})
    # 既存データをベースにして Scope のみ上書き（他のフィールドを消さない）
    updated = dict(existing)
    updated["name"] = name
    updated["owner"] = owner or existing.get("owner", "")
    updated["scope"] = scope.to_dict()
    updated.setdefault("is_public", False)
    now = datetime.now().isoformat(timespec="seconds")
    updated.setdefault("created_at", now)
    updated["updated_at"] = now
    index[key] = updated
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(index.values()), f, ensure_ascii=False, indent=2)
    return path


def _save_field(name: str, field: str, value: Any, owner: str = None, base_path: Path = None) -> Path:
    """指定ロジックの特定フィールドを更新する共通関数。"""
    path = _store_path(base_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    logics = load_all(base_path)
    index = _build_index(logics)
    # owner指定がある場合はキーで検索、ない場合は名前で検索
    target_key = None
    if owner is not None:
        target_key = f"{owner}::{name}"
    else:
        for k, r in index.items():
            if r.get("name") == name:
                target_key = k
                break
    if target_key is None or target_key not in index:
        return path
    index[target_key][field] = value
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(index.values()), f, ensure_ascii=False, indent=2)
    return path


def save_must(name: str, must: MustLogic, owner: str = None, base_path: Path = None) -> Path:
    """指定ロジックの Must を保存する。該当ロジックが無い場合は何もしない（Scope を先に保存すること）。"""
    return _save_field(name, "must", must.to_dict(), owner=owner, base_path=base_path)


def save_prefer_avoid(name: str, prefer_avoid: PreferAvoidLogic, owner: str = None, base_path: Path = None) -> Path:
    """指定ロジックの Prefer/Avoid を保存する。該当ロジックが無い場合は何もしない。"""
    return _save_field(name, "prefer_avoid", prefer_avoid.to_dict(), owner=owner, base_path=base_path)


def save_description(name: str, description: str, owner: str = None, base_path: Path = None) -> bool:
    """指定ロジックに説明文を保存する。"""
    path = _save_field(name, "description", description, owner=owner, base_path=base_path)
    return True


def save_custom_vars(name: str, custom_vars: CustomVariableSet, owner: str = None, base_path: Path = None) -> Path:
    """指定ロジックのカスタム変数を保存する。該当ロジックが無い場合は何もしない。"""
    return _save_field(name, "custom_vars", custom_vars.to_dict(), owner=owner, base_path=base_path)


def load_custom_vars(name: str, base_path: Path = None) -> Optional[CustomVariableSet]:
    """名前でロジックを検索し、カスタム変数セットを返す。無いか未設定なら None。"""
    r = get_logic(name, base_path=base_path)
    if r is None or r.get("custom_vars") is None:
        return None
    return CustomVariableSet.from_dict(r["custom_vars"])


def load_scope(name: str, base_path: Path = None) -> Optional[RaceScope]:
    """名前でロジックを検索し、Scope を返す。無ければ None。"""
    r = get_logic(name, base_path=base_path)
    if r is None:
        return None
    return RaceScope.from_dict(r.get("scope", {}))


def load_must(name: str, base_path: Path = None) -> Optional[MustLogic]:
    """名前でロジックを検索し、Must を返す。無いか未設定なら None。"""
    r = get_logic(name, base_path=base_path)
    if r is None or r.get("must") is None:
        return None
    return MustLogic.from_dict(r["must"])


def load_prefer_avoid(name: str, base_path: Path = None) -> Optional[PreferAvoidLogic]:
    """名前でロジックを検索し、Prefer/Avoid を返す。無いか未設定なら None。"""
    r = get_logic(name, base_path=base_path)
    if r is None or r.get("prefer_avoid") is None:
        return None
    return PreferAvoidLogic.from_dict(r["prefer_avoid"])


def set_public(name: str, is_public: bool, owner: str = None, base_path: Path = None) -> bool:
    """指定ロジックの公開/非公開を切り替える。該当ロジックが無い場合は False。"""
    path = _store_path(base_path)
    logics = load_all(base_path)
    index = _build_index(logics)
    target_key = None
    if owner is not None:
        target_key = f"{owner}::{name}"
    else:
        for k, r in index.items():
            if r.get("name") == name:
                target_key = k
                break
    if target_key is None or target_key not in index:
        return False
    index[target_key]["is_public"] = is_public
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(index.values()), f, ensure_ascii=False, indent=2)
    return True


def list_public_logics(base_path: Path = None) -> List[dict]:
    """公開されているロジック一覧を返す。"""
    return [r for r in load_all(base_path) if r.get("is_public", False)]


def delete_logic(name: str, owner: str = None, base_path: Path = None) -> bool:
    """指定名のロジックを削除する。削除できたら True、見つからなかったら False。"""
    path = _store_path(base_path)
    logics = load_all(base_path)
    index = _build_index(logics)
    target_key = None
    if owner is not None:
        target_key = f"{owner}::{name}"
    else:
        for k, r in index.items():
            if r.get("name") == name:
                target_key = k
                break
    if target_key is None or target_key not in index:
        return False
    del index[target_key]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(index.values()), f, ensure_ascii=False, indent=2)
    return True


def load_all(base_path: Path = None) -> List[dict]:
    """保存済みロジック一覧（name, scope, must, prefer_avoid）を返す。ファイル破損時は空リスト。"""
    path = _store_path(base_path)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def list_names(base_path: Path = None, owner: str = None) -> List[str]:
    """保存済みロジック名の一覧。owner 指定時はそのユーザーのもののみ返す。"""
    logics = load_all(base_path)
    if owner is not None:
        logics = [r for r in logics if r.get("owner", "") == owner]
    return [r.get("name", "") for r in logics if r.get("name")]


# ── フォワード成績の永続化（タスク 5.2） ──

def _forward_store_path(base: Path = None) -> Path:
    """フォワード成績の保存先。ロジックごとに別ファイル。"""
    if base is None:
        base = Path(__file__).resolve().parent.parent
    d = base / "data" / "forward"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _forward_safe_name(logic_name: str, owner: str = "") -> str:
    """フォワード成績ファイル名を生成。ownerを含めて衝突を防止。"""
    prefix = owner.replace("/", "_").replace("\\", "_") if owner else "_global"
    name = logic_name.replace("/", "_").replace("\\", "_")
    return f"{prefix}__{name}"


def save_forward_result(logic_name: str, result: ForwardResult, owner: str = "", base_path: Path = None) -> Path:
    """フォワード成績に1件追加する。"""
    record = load_forward_record(logic_name, owner=owner, base_path=base_path)
    if record is None:
        record = ForwardRecord(logic_name=logic_name)
    record.results.append(result)
    return _save_forward_record(record, owner=owner, base_path=base_path)


def _save_forward_record(record: ForwardRecord, owner: str = "", base_path: Path = None) -> Path:
    """フォワード成績全体を保存する。"""
    d = _forward_store_path(base_path)
    safe_name = _forward_safe_name(record.logic_name, owner)
    path = d / f"{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_forward_record(logic_name: str, owner: str = "", base_path: Path = None) -> Optional[ForwardRecord]:
    """指定ロジックのフォワード成績を読み込む。無ければ None。ownerなしの旧形式もフォールバック。"""
    d = _forward_store_path(base_path)
    safe_name = _forward_safe_name(logic_name, owner)
    path = d / f"{safe_name}.json"
    if not path.exists():
        # 旧形式のファイルもフォールバックで探す
        legacy_name = logic_name.replace("/", "_").replace("\\", "_")
        legacy_path = d / f"{legacy_name}.json"
        if legacy_path.exists():
            path = legacy_path
        else:
            return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return ForwardRecord.from_dict(json.load(f))
    except (json.JSONDecodeError, OSError):
        return None


def delete_forward_result(logic_name: str, index: int, owner: str = "", base_path: Path = None) -> bool:
    """フォワード成績の指定インデックスの結果を削除する。"""
    record = load_forward_record(logic_name, owner=owner, base_path=base_path)
    if record is None or index < 0 or index >= len(record.results):
        return False
    record.results.pop(index)
    _save_forward_record(record, owner=owner, base_path=base_path)
    return True
