#!/usr/bin/env python3
"""
ステータスに合わせて GitHub の Issue を自動更新するスクリプト。

docs/TASK_STATUS.json を参照し、ステータスが「完了」のタスクに対応する Issue のみクローズします。
「実装済みレビュー待ち」はクローズしません（Claude Code レビュー完了後に「完了」に変更してからクローズ）。

使い方:
  export GITHUB_TOKEN=ghp_xxxx
  python scripts/update_github_issues_progress.py           # 完了分をクローズ
  python scripts/update_github_issues_progress.py --dry-run  # 対象のみ表示

自動実行: push 時に GitHub Actions がこのスクリプトを実行する（docs/TASK_STATUS.json 変更時）。
"""
import json
import os
import urllib.request
import urllib.error
import argparse
from pathlib import Path

GITHUB_API = "https://api.github.com"
REPO_DEFAULT = "jinnext0711/predic_keiba"

# スクリプトから見た docs/TASK_STATUS.json のパス（リポジトリルート = scripts の親）
def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_task_status():
    """docs/TASK_STATUS.json を読み込む。無いか不正なら None。"""
    path = _repo_root() / "docs" / "TASK_STATUS.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_completed_title_keys():
    """ステータスが「完了」のタスクの Issue タイトルキー一覧を返す。"""
    data = load_task_status()
    if not data:
        return []
    status = data.get("status", {})
    keys = data.get("task_title_keys", {})
    return [keys[t] for t, s in status.items() if s == "完了" and t in keys and keys[t]]


def list_open_issues(token: str, repo: str) -> list:
    """オープンな Issue 一覧を取得。"""
    url = f"{GITHUB_API}/repos/{repo}/issues?state=open&per_page=100"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
    return [i for i in data if "pull_request" not in i]


def close_issue(token: str, repo: str, issue_number: int, comment: str = None) -> bool:
    """Issue をクローズ。オプションでコメントを追加。"""
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
    data = json.dumps({"state": "closed"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"  Close failed: {e.code} {e.read().decode()}")
        return False
    if comment:
        url_comment = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
        req_c = urllib.request.Request(
            url_comment,
            data=json.dumps({"body": comment}).encode("utf-8"),
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req_c)
        except urllib.error.HTTPError:
            pass
    return True


def main():
    parser = argparse.ArgumentParser(description="docs/TASK_STATUS.json に基づき GitHub Issue を更新")
    parser.add_argument("--dry-run", action="store_true", help="クローズせず対象 Issue のみ表示")
    parser.add_argument("--comment", action="store_true", help="クローズ時に進捗コメントを追加")
    args = parser.parse_args()

    completed_keys = get_completed_title_keys()
    if not completed_keys:
        print("docs/TASK_STATUS.json が無いか、ステータス「完了」のタスクがありません。")
        print("リポジトリルート: ", _repo_root())
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token and not args.dry_run:
        print("GITHUB_TOKEN を設定してください。（--dry-run の場合はトークン不要）")
        return 1
    repo = os.environ.get("GITHUB_REPO", REPO_DEFAULT)
    print(f"リポジトリ: {repo}")
    print(f"クローズ対象（ステータス=完了）: {completed_keys}")

    if not token:
        print("GITHUB_TOKEN を設定すると、クローズ対象の Issue 番号も表示できます。")
        return 0

    issues = list_open_issues(token, repo)
    to_close = []
    for i in issues:
        title = i.get("title", "")
        for key in completed_keys:
            if key in title:
                to_close.append((i["number"], title))
                break

    if not to_close:
        print("クローズ対象のオープン Issue はありません。")
        return 0

    print(f"\nクローズ対象: {len(to_close)} 件")
    for num, title in to_close:
        print(f"  #{num} {title}")

    if args.dry_run:
        print("\n--dry-run のためクローズしません。")
        return 0

    comment_text = None
    if args.comment:
        comment_text = "ステータスを「完了」に更新したためクローズしました。（docs/TASK_STATUS.json に基づく）"

    closed = 0
    for num, title in to_close:
        if close_issue(token, repo, num, comment_text):
            closed += 1
            print(f"Closed #{num} {title}")
    print(f"\n完了: {closed}/{len(to_close)} 件をクローズしました。")
    return 0


if __name__ == "__main__":
    exit(main())
