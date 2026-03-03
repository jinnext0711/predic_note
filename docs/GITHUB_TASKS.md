# GitHub でタスクを管理する

開発タスクは GitHub Issues で管理します。`docs/DEV_TASKS.md` の内容を Issue として登録できます。

---

## 方法1: スクリプトで一括作成（推奨）

1. **Personal Access Token の取得**
   - ブラウザで次のURLを開く（GitHub にログインした状態で）:
     - **Classic トークン**: https://github.com/settings/tokens
     - **Fine-grained トークン**: https://github.com/settings/personal-access-tokens
   - **Generate new token**（Classic の場合は **Generate new token (classic)**）をクリック
   - **Note**: 用途が分かる名前を入力（例: `predic_keiba Issue 作成`）
   - **Expiration**: 有効期限を選択（例: 90 days）
   - **Scopes（Classic の場合）**: **repo** にチェック（Issue・ラベル作成に必要）
   - **Permissions（Fine-grained の場合）**: Repository access で対象リポジトリを選び、Permissions で **Issues: Read and write** などリポジトリ権限を付与
   - **Generate token** をクリック
   - 表示された **ghp_で始まる文字列** がトークンです。**この画面を離れると二度と表示されない**ので、必ずコピーして安全な場所に保存する

2. **作成予定の確認（dry-run）**
   ```bash
   cd /Users/jinnobuta/test/predic_keiba
   python3 scripts/create_github_issues.py --dry-run
   ```

3. **スクリプトを実行**
   ```bash
   export GITHUB_TOKEN=ghp_xxxx   # あなたのトークンに置き換え
   python3 scripts/create_github_issues.py
   ```

4. **リポジトリを変える場合**
   ```bash
   export GITHUB_REPO=owner/repo名
   python3 scripts/create_github_issues.py
   ```
   デフォルトは `jinnext0711/predic_keiba` です。リポジトリ名が違う場合は必ず指定してください。

実行すると、`docs/DEV_TASKS.md` に沿った Issue が作成され、必要なラベルが自動作成されます。

### Issue が反映されないとき

- **リポジトリが 404** … `GITHUB_REPO` が正しいか確認。GitHub 上で `https://github.com/ユーザー名/リポジトリ名` が存在するか確認。
- **トークンエラー** … トークンに `repo` スコープがあるか、有効期限切れでないか確認。
- **ラベルだけ付かない** … Issue は作成されていてラベルのみ失敗している場合があります。その場合は Issue 一覧で確認し、手動でラベルを付けてください。

---

## ステータスに合わせて Issue を自動更新する（推奨）

**正（Single Source of Truth）**: `docs/TASK_STATUS.json`

このファイルの `status` だけを更新すれば、GitHub の Issue ステータスと同期できます。

### ステータスの意味

| ステータス | 意味 | GitHub Issue |
|-----------|------|--------------|
| `未着手` | まだ着手していない | オープンのまま |
| `実装済みレビュー待ち` | 実装済み。Claude Code でのレビュー未了 | オープンのまま（クローズしない） |
| `完了` | 実装 + Claude Code レビュー完了 | 該当 Issue を **クローズ** する |

**ルール**: レビューが終わったタスクだけ `完了` にし、push すると GitHub Actions が該当 Issue をクローズします。

### 自動同期の流れ

1. `docs/TASK_STATUS.json` の `status` で、該当タスクを `完了` に変更する。
2. 変更をコミットして **push** する（`main` / `master` へ）。
3. `.github/workflows/update-issue-status.yml` が動き、ステータスが「完了」のタスクに対応するオープンな Issue をクローズする。

※ `docs/TASK_STATUS.json` または `scripts/update_github_issues_progress.py` を変更した push のときだけワークフローが実行されます。

### 手動でスクリプトを実行する場合

1. **対象の確認（dry-run）**
   ```bash
   cd predic_keiba
   export GITHUB_TOKEN=ghp_xxxx
   python3 scripts/update_github_issues_progress.py --dry-run
   ```
   `TASK_STATUS.json` で「完了」になっているタスクのうち、オープンな Issue がクローズ対象として表示されます。

2. **実行してクローズ**
   ```bash
   export GITHUB_TOKEN=ghp_xxxx
   python3 scripts/update_github_issues_progress.py
   ```

3. **クローズ時にコメントを残す**
   ```bash
   python3 scripts/update_github_issues_progress.py --comment
   ```

新規タスクの Issue をスクリプトでクローズ対象に含めるには、`docs/TASK_STATUS.json` の `task_title_keys` に `"番号": "[番号] タイトル"` を追加し、`status` でその番号を `完了` にしてください。

---

## 方法2: 手動で Issue を作成

1. リポジトリの **Issues** タブを開く
2. **New issue** をクリック
3. テンプレートから **開発タスク** を選ぶ（`.github/ISSUE_TEMPLATE/task.md`）
4. `docs/DEV_TASKS.md` の表を参照して、タイトル・内容・備考を入力

---

## ラベル（スクリプトで自動作成されるもの）

| ラベル | 用途 |
|--------|------|
| `phase-1` 〜 `phase-5` | マイルストーン |
| `data` | データ基盤 |
| `ui` | UI・画面 |
| `backend` | 永続化・API |
| `simulation` | シミュレーション・バックテスト |
| `derived` | 導出指標 |
| `auth` | 認証・有料 |
| `infra` | テスト・CI |
| `docs` | ドキュメント |

---

## GitHub Projects でかんばんにする場合

1. リポジトリの **Projects** タブで **New project** を選択
2. **Board** を選び、**Issues** をソースに設定
3. ステータス列（例: Todo / In progress / Done）を追加
4. 作成した Issue をドラッグして進捗管理

---

## 参照

- タスク一覧の詳細: `docs/DEV_TASKS.md`
- MVP 要件: `docs/MVP_SPEC.md`
