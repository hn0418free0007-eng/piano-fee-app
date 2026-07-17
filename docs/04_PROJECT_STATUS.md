# PROJECT STATUS

## 最終更新日

2026-07-17

## 現在の状態

- システム名: ピアノ教室運営アプリ Ver.3
- Repository: `piano-fee-app`
- 本番ブランチ: `main`
- Streamlit起動ファイル: `local_web_app/app.py`
- GitHub、Streamlit Community Cloud、Supabase、Google OAuth、Google Calendar APIの接続は完了しています。
- Google Calendar予定の取得、生徒照合、9,000円の受領登録まで本番相当環境で確認済みです。
- 今日の受付では、受領後に「今日の売上9,000円・受領済み1名・未受領0名」になることを確認済みです。
- 売上管理・確定申告画面で40,000円と表示された原因は未調査です。
- Identity Sequence自動同期のコードとSQLには未コミット変更が残っています。内容確認・テスト・分離コミットが必要です。

## 次回最優先

次回は、必ず次の順序で進めます。

1. `docs/08_CHATGPT引継ぎ.md` と本ファイルを読む。
2. `git status` と `git diff` でIdentity Sequence関連の未コミット変更を確認する。
3. 新規SQL・テストファイルを直接開くか `git diff --no-index` で確認する。
4. Identity Sequence関連テストを実行する。
5. 問題がなければ対象4ファイルだけを `Add Supabase identity sequence synchronization` でコミットし、`origin/main` へpushする。
6. Streamlit本番環境でログイン、Calendar取得、今日の受付、受領登録を確認する。
7. 売上管理・確定申告画面の40,000円表示の原因を調査する。
8. 売上調査後に受領取消処理を確認する。
9. 作業終了前に本ファイルと `docs/08_CHATGPT引継ぎ.md` を更新する。

## 完成済み

- [x] GitHub連携
- [x] Streamlit Community Cloudへの公開
- [x] Supabase接続
- [x] Supabase PostgreSQLとRLS
- [x] Google OAuth
- [x] PKCE verifierの外部リダイレクト対応
- [x] Google Calendar API連携
- [x] Google Calendar予定と生徒の自動照合
- [x] 手動照合結果の保存
- [x] SQLiteからSupabaseへのデータ移行
- [x] 今日の受付
- [x] 受領登録
- [x] Identity Sequence同期の実装
- [x] 受領登録時のduplicate keyエラー対策
- [x] プロジェクトドキュメント8ファイルの作成
- [x] `docs/` のGitHubへのpush
- [x] ローカルデモモードと自動テスト

## 動作確認済み

- [x] Google Calendarの予定を取得できる
- [x] Calendar予定から生徒を照合できる
- [x] 9,000円の受領登録ができる
- [x] 受領後に今日の売上が9,000円になる
- [x] 受領後に受領済み1名になる
- [x] 受領後に未受領0名になる

## 未完了

- [ ] 売上管理・確定申告画面で40,000円と表示される原因調査
- [ ] 受領取消処理の動作確認
- [ ] CSV出力の確認・改善
- [ ] Excel出力の確認・改善
- [ ] 本番データでの総合運用テスト
- [ ] `docs/01_URL一覧.md` の未設定になっている本番URL・Project名の追記
- [ ] Identity Sequence関連の未コミット変更の最終確認・コミット・push

## 既知の問題

### 売上管理・確定申告画面が40,000円

確認済みの事実:

- 9,000円の受領登録自体は正常です。
- 今日の受付画面では売上9,000円です。
- 別の売上管理・確定申告画面では40,000円と表示されました。
- 表示内訳として22,000円と18,000円が見えていました。

次回の確認ポイント:

- `payments` ではなく `charges` を集計していないか
- `amount_received` ではなく `charge_amount` を使っていないか
- 取消済み入金を除外しているか
- 対象期間の絞り込みが正しいか
- SQLite由来のサンプルデータが含まれていないか
- 同じ入金を重複集計していないか
- Supabase移行前の古い集計ロジックが残っていないか

修正前に原因、対象ファイル、修正方針を説明します。

### Identity Sequence関連変更が未コミット

Identity列へSQLiteのIDを明示して移行した後、PostgreSQLシーケンスを最大IDへ同期する修正です。内容確認とテスト後に、ほかの変更と混ぜずコミットします。

## 現在のGit状態

`docs/` の8ファイルは、次のコミットでGitHubへpush済みです。

- コミットID: `00983e86d879d39d32bc9a15ba175768f4196547`
- コミットメッセージ: `Add project documentation`
- このコミット時点で `main` と `origin/main` は同期済みです。

現在は、次のIdentity Sequence関連変更が未コミットです。

```text
 M local_web_app/migrate_to_supabase.py
 M local_web_app/supabase_schema.sql
?? local_web_app/supabase_sequence_sync.sql
?? local_web_app/tests/test_migrate_to_supabase.py
```

記号の意味:

- `M`: Git管理済みの既存ファイルが変更されている状態
- `??`: Gitでまだ管理されていない新規ファイル

これらはエラーではありません。内容とテストを確認し、必要な変更だけを別コミットへ含める予定です。破棄、reset、checkout、cleanを実行しないでください。

## 次回の作業順序

### 1. 引継ぎ資料を読む

- `docs/08_CHATGPT引継ぎ.md`
- `docs/04_PROJECT_STATUS.md`

### 2. Git差分を確認する

```powershell
git status
git diff
git diff --no-index NUL local_web_app/supabase_sequence_sync.sql
git diff --no-index NUL local_web_app/tests/test_migrate_to_supabase.py
```

`git diff --no-index` がWindows環境で使えない場合は、新規ファイルを直接開きます。

### 3. Identity Sequenceテストを実行する

Repositoryルートからの例:

```powershell
.\local_web_app\.venv\Scripts\python.exe -m pytest local_web_app/tests/test_migrate_to_supabase.py
```

### 4. 対象4ファイルだけコミットする

```powershell
git add local_web_app/migrate_to_supabase.py
git add local_web_app/supabase_schema.sql
git add local_web_app/supabase_sequence_sync.sql
git add local_web_app/tests/test_migrate_to_supabase.py
git diff --cached
git commit -m "Add Supabase identity sequence synchronization"
git push origin main
git status
git log -1 --oneline
```

### 5. Streamlit本番確認

- 正常起動
- Googleログイン
- Calendar取得
- 今日の受付表示
- 受領登録
- エラーがない

### 6. 売上40,000円表示を調査する

原因を確認してから、対象ファイルと修正方針を説明します。

### 7. 受領取消処理を確認する

- `payments` を物理削除しない
- `cancelled_at` と取消理由が保存される
- `charges` が未受領相当へ戻る
- 受領済み人数と売上から除外される
- `audit_logs` に履歴が残る

### 8. 文書を更新する

本ファイルと `docs/08_CHATGPT引継ぎ.md` を必ず最新化します。

## 直近のコミット

| コミット | メッセージ | 内容 |
|---|---|---|
| `00983e86d879d39d32bc9a15ba175768f4196547` | `Add project documentation` | `docs/` の8ファイルを追加してpush |
| `85ee4c8` | `Fix OAuth PKCE verifier persistence` | PKCE verifier永続化 |
| `1b35830` | `Fix Streamlit config location` | Streamlit設定を起動ファイル側へ配置 |

## 更新履歴

| 日付 | 変更内容 | 状態 |
|---|---|---|
| 2026-07-17 | 現在のGit状態、動作確認済み内容、40,000円問題、次回8段階手順を追記 | 完了 |
| 2026-07-17 | プロジェクトドキュメント8ファイルを作成しGitHubへpush | 完了 |
| 2026-07-17 | Identity Sequence同期を実装 | 未コミット・確認待ち |
| 2026-07-17 | PKCE verifier永続化を実装・push | 完了 |

更新時は、新しい行を表の先頭へ追加してください。
