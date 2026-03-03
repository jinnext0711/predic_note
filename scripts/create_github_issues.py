#!/usr/bin/env python3
"""
GitHub に開発タスクの Issue を一括作成するスクリプト。

使い方:
  export GITHUB_TOKEN=ghp_xxxx   # Personal Access Token (repo scope)
  python scripts/create_github_issues.py

リポジトリ: 環境変数 GITHUB_REPO で上書き可能（デフォルト: jinnext0711/predic_keiba）
"""
import json
import os
import urllib.request
import urllib.error

GITHUB_API = "https://api.github.com"
REPO_DEFAULT = "jinnext0711/predic_keiba"

ISSUES = [
    # 1. データ基盤
    {
        "title": "[1.1] レース・馬データ取得",
        "body": """## 概要
中央競馬・過去5年・平地・未勝利戦以上のレース・馬データの取得・保存。

## 内容
- データソースの選定（公式/非公式API or スクレイピング）
- 取得・保存パイプラインの実装

## ラベル
- `phase-1` `data`
""",
        "labels": ["phase-1", "data"],
    },
    {
        "title": "[1.2] オッズデータ",
        "body": """## 概要
発走直前最終オッズの取得・紐付け。

## 内容
- オッズデータの取得
- レース・馬との紐付け（シミュレーションで必須）

## ラベル
- `phase-1` `data`
""",
        "labels": ["phase-1", "data"],
    },
    {
        "title": "[1.3] 血統データ（5世代）",
        "body": """## 概要
5世代血統の保持・事前定義指標の導出。

## 内容
- 5世代血統データの保持
- 事前定義指標の導出（父系・母父系・距離適性・芝/ダート・インブリード）
- 生ツリーは編集不可、指標のみロジックで使用

## ラベル
- `phase-1` `data`
""",
        "labels": ["phase-1", "data"],
    },
    # 2. ロジック編集UI
    {
        "title": "[2.1] Scope 編集の確定",
        "body": """## 概要
競馬場・距離・芝/ダート・クラス・年齢の選択UIを完成させ、ロジック記録に保存。

## 内容
- 選択UIの完成（現状は選択＋検証のみ）
- ロジック記録への保存

## ラベル
- `phase-1` `ui`
""",
        "labels": ["phase-2", "ui"],
    },
    {
        "title": "[2.2] Must 条件編集",
        "body": """## 概要
ブロック単位で条件追加・同一ブロック内OR・ブロック間AND の編集UI。

## 内容
- Must ブロックの追加/削除/編集UI
- 使用可能データ項目に制限

## ラベル
- `phase-2` `ui`
""",
        "labels": ["phase-2", "ui"],
    },
    {
        "title": "[2.3] Prefer / Avoid 編集",
        "body": """## 概要
Prefer 最大5個・並び替え、Avoid 最大2個の編集UI。

## 内容
- Prefer / Avoid 条件の編集・並び替え
- レキシコグラフィック順で評価されることをUIで明示

## ラベル
- `phase-2` `ui`
""",
        "labels": ["phase-2", "ui"],
    },
    {
        "title": "[2.4] カスタム変数編集",
        "body": """## 概要
最大3個・型（真偽値/3段階/数値）の設定UI。

## 内容
- カスタム変数の追加/編集（最大3個）
- 型選択: 真偽値・3段階カテゴリ・数値
- 含むとシミュレーション不可になる旨の表示

## ラベル
- `phase-2` `ui`
""",
        "labels": ["phase-2", "ui"],
    },
    # 3. 導出指標
    {
        "title": "[3.1] 逃げ馬数・先行馬数",
        "body": """## 概要
レース単位で逃げ・先行馬の数を算出。

## 内容
- 定義は固定（MVP_SPEC）
""",
        "labels": ["phase-1", "derived"],
    },
    {
        "title": "[3.2] 前走位置平均との差",
        "body": """## 概要
馬ごとに前走4角位置平均との差を算出。

## 内容
- 定義は固定（MVP_SPEC）
""",
        "labels": ["phase-1", "derived"],
    },
    {
        "title": "[3.3] レースペース分類",
        "body": """## 概要
速／普／遅の簡易分類を実装。

## 内容
- 定義は固定（MVP_SPEC）
""",
        "labels": ["phase-1", "derived"],
    },
    # 4. シミュレーション
    {
        "title": "[4.1] シミュレーション可能判定の確定・UI表示",
        "body": """## 概要
ロジック種別に応じた可否判定の確定・UI表示。

## 内容
- 既存モデルで判定済みのため、UI表示の明確化
""",
        "labels": ["phase-3", "simulation"],
    },
    {
        "title": "[4.2] バックテストエンジン",
        "body": """## 概要
単勝・複勝・100円換算・最終オッズ固定で過去5年を再計算。

## 内容
- シミュレーション可能ロジックのみ対象
""",
        "labels": ["phase-3", "simulation"],
    },
    {
        "title": "[4.3] シミュレーション結果表示",
        "body": """## 概要
試行回数・回収率・的中率・年別推移・最大ドローダウン・最大連敗数の表示。

## 内容
- 有料機能として制御
""",
        "labels": ["phase-3", "simulation"],
    },
    # 5. ロジック記録・成績
    {
        "title": "[5.1] ロジックの永続化",
        "body": """## 概要
Scope / Must / Prefer-Avoid / カスタム変数をDB or ファイルで保存。
""",
        "labels": ["phase-2", "backend"],
    },
    {
        "title": "[5.2] フォワード成績の記録",
        "body": """## 概要
実運用で的中・払戻を記録し表示。無料機能。
""",
        "labels": ["phase-2", "backend"],
    },
    {
        "title": "[5.3] ロジック一覧・詳細画面",
        "body": """## 概要
保存したロジックの一覧・編集・削除。
""",
        "labels": ["phase-2", "ui"],
    },
    # 6. 認証・有料
    {
        "title": "[6.1] 認証",
        "body": """## 概要
ユーザー登録・ログイン。
""",
        "labels": ["phase-4", "auth"],
    },
    {
        "title": "[6.2] 有料プランと制限",
        "body": """## 概要
自分のロジックのバックテストは有料、他人の公開ロジックは回数制限。MVP_SPEC 8。
""",
        "labels": ["phase-4", "auth"],
    },
    {
        "title": "[6.3] 公開ロジック",
        "body": """## 概要
他人に公開するロジックの公開/非公開設定。
""",
        "labels": ["phase-4", "backend"],
    },
    # 7. 後工程
    {
        "title": "[7.1] UI リッチ化",
        "body": """## 概要
レイアウト・コンポーネント・レスポンシブ・アクセシビリティの強化。**後工程で検討**。
""",
        "labels": ["phase-5", "ui"],
    },
    {
        "title": "[7.2] テスト・CI",
        "body": """## 概要
単体テスト・結合テスト・CI パイプライン。
""",
        "labels": ["phase-5", "infra"],
    },
    {
        "title": "[7.3] ドキュメント・ヘルプ",
        "body": """## 概要
利用ガイド・API ドキュメント（必要に応じて）。
""",
        "labels": ["phase-5", "docs"],
    },
]


def create_issue(token: str, repo: str, title: str, body: str, labels: list = None) -> dict:
    """Issue を作成。ラベルは先に渡さず、作成後に PATCH で付与する（存在しないラベルで 422 を防ぐ）。"""
    url = f"{GITHUB_API}/repos/{repo}/issues"
    payload = {"title": title, "body": body}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read().decode())
    if labels:
        add_labels_to_issue(token, repo, result["number"], labels)
    return result


def add_labels_to_issue(token: str, repo: str, issue_number: int, labels: list) -> None:
    """既存 Issue にラベルを付与。ラベルが存在しない場合はスキップ。"""
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
    data = json.dumps({"labels": labels}).encode("utf-8")
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
        if e.code != 422:
            raise
        # 422 = ラベルが存在しないなど。Issue は作成済みなので警告のみ
        print(f"  (Warning: labels not applied for #{issue_number})")


def ensure_labels(token: str, repo: str) -> bool:
    """ラベルが存在しない場合は作成。リポジトリが存在しない場合は False。"""
    labels_wanted = {"task"}  # Issue テンプレート用
    for issue in ISSUES:
        labels_wanted.update(issue.get("labels", []))
    url = f"{GITHUB_API}/repos/{repo}/labels"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            existing = {lb["name"] for lb in json.loads(res.read().decode())}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"警告: リポジトリ {repo} が見つかりません。URL と GITHUB_REPO を確認してください。")
            return False
        existing = set()
    for name in labels_wanted:
        if name in existing:
            continue
        data = json.dumps({"name": name, "color": "ededed"}).encode("utf-8")
        r = urllib.request.Request(
            url, data=data,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if e.code != 422:  # 422 = already exists
                raise
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub に開発タスク Issue を一括作成")
    parser.add_argument("--dry-run", action="store_true", help="API を呼ばず、作成予定の Issue 一覧を表示")
    args = parser.parse_args()

    if args.dry_run:
        print(f"作成予定の Issue: {len(ISSUES)} 件")
        for i, issue in enumerate(ISSUES, 1):
            print(f"  {i}. {issue['title']} (labels: {issue.get('labels', [])})")
        print("\n実行するには: export GITHUB_TOKEN=ghp_xxxx && python3 scripts/create_github_issues.py")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN を設定してください。例: export GITHUB_TOKEN=ghp_xxxx")
        print("トークンは GitHub → Settings → Developer settings → Personal access tokens で発行")
        return 1
    repo = os.environ.get("GITHUB_REPO", REPO_DEFAULT)
    print(f"リポジトリ: https://github.com/{repo}")
    ensure_labels(token, repo)
    created = 0
    for issue in ISSUES:
        title = issue["title"]
        body = issue["body"]
        labels = issue.get("labels", [])
        try:
            result = create_issue(token, repo, title, body, labels)
            created += 1
            print(f"Created: #{result['number']} {title}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode() if e.fp else ""
            print(f"Error creating '{title}': {e.code} {err_body}")
            if e.code == 404:
                print("リポジトリが存在しないか、トークンの権限が不足しています。")
    print(f"\n完了: {created}/{len(ISSUES)} 件の Issue を作成しました。")
    return 0


if __name__ == "__main__":
    exit(main())
