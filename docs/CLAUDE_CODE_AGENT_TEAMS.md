# Claude Code エージェントチームの利用

このプロジェクトでは [Claude Code のエージェントチーム](https://code.claude.com/docs/ja/agent-teams) が利用できるように設定しています。

## 有効化の確認

次のいずれかで有効になっています。

- **ユーザー全体**: `~/.claude/settings.json` に `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` を設定済み
- **このプロジェクトのみ**: `predic_keiba/.claude/settings.local.json` に同様の設定を追加済み
- **表示**: `teammateMode: "tmux"` により、エージェントチーム起動時は**分割ペイン**がデフォルト（各チームメイトを個別ペインで並列表示）

**分割ペインに必要**: ターミナルに **tmux** が入っていること。iTerm2 の場合は `tmux -CC` でタブ分割表示。未導入のときは自動でインプロセス（1画面）にフォールバックします。

Claude Code を**再起動**したうえで、チーム機能が使えるか確認してください。

## エージェントチームの起動方法

1. Claude Code でこのプロジェクトのディレクトリを開く（`predic_keiba` またはその親）。
2. チャットで、**エージェントチームを作成する**旨を自然言語で指示する。

例（日本語）:

```
predic_keiba の開発タスクを進めたい。エージェントチームを作ってほしい。
役割は次の3つで並列に進めてほしい：
- 1人目: データ層（data/）の実装・修正
- 2人目: UI（app.py）の改善
- 3人目: ドキュメント・テストの整備
```

例（英語・公式ドキュメント風）:

```
Create an agent team to explore this codebase from different angles:
one teammate on data pipeline, one on Streamlit UI, one on tests and docs.
```

3. Claude がチームを作成し、チームメイトを起動してタスクを振り分けます。
4. **Shift+Down** でチームメイトを切り替え、直接メッセージを送れます。
5. 作業が終わったら「チームをクリーンアップして」と指示して終了します。

## 公式ドキュメント

- [Claude Code セッションのチームを調整する](https://code.claude.com/docs/ja/agent-teams) … チームの開始・制御・ベストプラクティス

## 注意（実験的機能）

- エージェントチームは**実験的**です。セッション再開・タスク調整・シャットダウンに制限があります。
- トークン消費は単一セッションより多くなります。並列で価値が出るタスク（調査・レビュー・別モジュールの実装）に向いています。
