# ピアノ教室運営アプリ Ver.3 — 本番導入・運用手順

先生がスマートフォンで「今日のGoogleカレンダー確認 → 封筒へ押印 → 受領・押印済みボタン」まで完了するStreamlitアプリです。本番はSupabase PostgreSQL・Supabase Authentication・Google Calendar APIを使います。外部設定がない場合はSQLiteと架空予定のデモモードになります。

## 1. 実装されている機能

- Supabase接続、Google Providerログイン、許可メールの二重制限（アプリ設定＋Supabase RLS）
- Google Calendar APIから今日0:00〜翌日0:00の予定を取得し、開始時刻順に表示
- 氏名照合：前後空白、全角・半角スペース、連続空白、末尾の「レッスン」を安全に正規化
- 候補が一人の場合だけ自動照合。曖昧・不一致は未照合のまま手動選択し、対応を保存
- 受領・押印済み1ボタン。PostgreSQL行ロックを使い、残額確認・入金・請求更新・監査を1トランザクションで実行
- 生徒管理、月次請求、発表会費、未入金、月別・年間・生徒別・発表会費売上
- UTF-8 BOM付きCSV、Excel、SQLiteからSupabaseへの読み取り専用移行
- スマートフォン向けカード、縦配置、大型ボタン

## 2. ローカル確認

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
streamlit run app.py
```

設定がなければ「デモ・ローカルモード」と表示されます。実名ではない予定を使うため、本番DBへは接続しません。

## 3. 本番設定 — 必ず順番どおりに実施

### 手順1：GitHubへ配置する

1. GitHubでPrivate repositoryを作ります。
2. `local_web_app` の内容をリポジトリ直下へ配置します。`app.py` と `requirements.txt` が同じ階層になるようにします。
3. `.streamlit/secrets.toml`、`.env`、`data/*.db`、`backup/*.db` がGitへ含まれていないことを確認します。
4. `.streamlit/secrets.toml.example` と `.env.example` は見本なので登録して構いません。

### 手順2：Supabaseプロジェクトを作る

1. `https://supabase.com/dashboard` へログインし、`New project` を押します。
2. Organization、Project name、Database password、Regionを入力します。Regionは利用場所に近いものを選びます。
3. `Create new project` を押し、準備完了まで待ちます。Database passwordはパスワード管理ソフトへ保存します。
4. 左メニューの `Project Settings` → `API` を開きます。
5. `Project URL` を控えます。これはSecretsの `supabase.url` です。
6. `Publishable key`（旧画面では `anon public`）を控えます。これは `supabase.anon_key` です。`service_role` はアプリへ登録しません。

### 手順3：テーブルとRLSを作る

1. Supabase左メニューの `SQL Editor` → `New query` を押します。
2. [supabase_schema.sql](supabase_schema.sql) の全内容を貼り付け、`Run` を押します。
3. エラーがないことを確認します。
4. SQL末尾の例を使い、許可する先生のGoogleメールを登録します。

```sql
insert into allowed_teachers(email, display_name)
values ('実際の先生のGoogleメール', '先生');
```

5. 複数の先生を許可する場合だけ、一人ずつ追加します。この表にないメールはRLSで生徒・請求・入金へアクセスできません。

### 手順4：Google Cloudプロジェクトを作る

1. `https://console.cloud.google.com/` を開きます。
2. 上部のプロジェクト選択 → `新しいプロジェクト` を押します。
3. プロジェクト名を入力して `作成` を押し、作成したプロジェクトへ切り替えます。
4. `APIとサービス` → `ライブラリ` を開き、`Google Calendar API` を検索します。
5. `Google Calendar API` → `有効にする` を押します。
6. `Google Auth Platform` → `Branding` でアプリ名、サポートメール、連絡先メールを設定します。
7. `Audience` で利用範囲を設定します。個人Googleアカウントなら通常 `External`、Google Workspace内部だけなら管理方針に従い `Internal` を選びます。テスト状態では先生のメールをTest usersへ追加します。
8. `Data Access` でCalendarの読取専用スコープ `.../auth/calendar.readonly` を確認します。

### 手順5：Google OAuthクライアントを作る

この手順ではSupabaseが表示するCallback URLをGoogleへ貼ります。

1. Supabase → `Authentication` → `Providers` → `Google` を開きます。
2. `Callback URL`（通常 `https://<project-ref>.supabase.co/auth/v1/callback`）をコピーします。
3. Google Cloud → `Google Auth Platform` → `Clients` → `Create client` を押します。
4. Application typeは `Web application` を選びます。
5. `Authorized redirect URIs` → `Add URI` に、手順2でコピーしたSupabase Callback URLを貼ります。文字を変更せず、末尾まで一致させます。
6. `Create` を押し、表示された `Client ID` と `Client secret` を一時的に控えます。
7. SupabaseのGoogle Provider画面へ戻り、Client IDとClient secretをそれぞれ貼ります。
8. Google Providerを `Enabled` にして `Save` を押します。Client secretをGitやREADMEへ書かないでください。

### 手順6：Streamlit Community Cloudへ仮デプロイする

1. `https://share.streamlit.io/` へログインします。
2. `Create app` → `Yup, I have an app` を押します。
3. GitHub repository、branch、Main file pathの `app.py` を選びます。
4. 任意のApp URLを決め、`Deploy` を押します。最初はSupabase Secretsを入れずデモ起動して構いません。
5. 発行された `https://xxxx.streamlit.app` を正確にコピーします。これが `app.public_url` です。HTTPSはCommunity Cloudが提供します。

### 手順7：Redirect URLをSupabaseへ登録する

1. Supabase → `Authentication` → `URL Configuration` を開きます。
2. `Site URL` にStreamlitの `https://xxxx.streamlit.app` を貼ります。
3. `Redirect URLs` に同じURLを追加します。アプリのURLにパスや末尾 `/` がある場合はSecretsの値と完全に揃えます。
4. ローカル認証テストをする場合だけ `http://127.0.0.1:8501` も追加します。本番確認後、不要なら削除します。

### 手順8：Streamlit Secretsを登録する

1. Streamlit workspaceでアプリの `︙` → `Settings` → `Secrets` を開きます。
2. `.streamlit/secrets.toml.example` を基に、次を貼ります。`allowed_emails` は手順3と同じメールだけにします。

```toml
[app]
mode = "cloud"
timezone = "Asia/Tokyo"
public_url = "https://xxxx.streamlit.app"
allowed_emails = ["実際の先生のGoogleメール"]

[supabase]
url = "Supabase Project URL"
anon_key = "Supabase Publishable key"

[google_calendar]
calendar_id = "primary"
```

3. `Save` を押し、アプリをRebootします。
4. Googleログイン画面が表示されることを確認します。許可外メールで入れないことも必ず確認します。

### 手順9：SQLiteデータを移行する

まずプレビューします。元SQLiteは読み取り専用で開かれます。

```powershell
python migrate_to_supabase.py
```

件数とSHA-256を確認します。本番移行時だけPowerShellの現在セッションへ値を設定します。

```powershell
$env:SUPABASE_URL="https://xxxx.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="Supabaseのservice_role key"
python migrate_to_supabase.py --commit
```

`MIGRATE` と入力した場合だけ実行します。既存主キーは上書きせずスキップし、成功・スキップ・エラー件数をテーブル別に表示します。全件成功後はSQLiteのSHA-256を `migration_runs` へ保存し、同じファイルの二重移行を拒否します。終了後はPowerShellを閉じ、service-role keyを残さないでください。

### 手順10：スマートフォンから使う

1. スマートフォンのSafariまたはChromeでStreamlitのHTTPS URLを開きます。
2. `Googleでログイン` を押し、許可済み先生アカウントを選びます。
3. 初回だけCalendar読取権限を確認して許可します。
4. ブラウザメニューの「ホーム画面に追加」を使うと、次回からアイコンで開けます。
5. Googleトークン期限切れで予定取得エラーになった場合は、サイドバーからログアウトして再ログインします。

## 4. カレンダー照合の安全ルール

完全一致を基本とし、空白正規化と末尾の「レッスン」だけを補助的に除きます。正規化後の候補が一人だけなら自動照合します。同名候補、別表記、不一致は自動登録せず `未照合` と表示します。先生が生徒を選択して保存した対応だけを次回利用します。予定タイトルを大きく変更した場合は別の未照合として扱います。

## 5. 本番運用前チェックリスト

- [ ] 許可した先生のGoogleアカウントでログインできる
- [ ] 許可していないGoogleアカウントは入れない
- [ ] 今日のGoogleカレンダー予定が時刻順に取得できる
- [ ] 生徒名が正しく照合され、曖昧な予定は未照合になる
- [ ] スマートフォンで文字が読め、受領ボタンが押しやすい
- [ ] 受領・押印済み登録がSupabase `payments` に保存される
- [ ] 同じ請求の二重登録が拒否される
- [ ] 月別・年間・生徒別売上へ反映される
- [ ] 月別売上、年間売上、生徒別売上、発表会費、未入金をCSV/Excel出力できる
- [ ] Supabase Dashboardからデータを確認できる
- [ ] Supabaseのバックアップ/PITR契約、または定期エクスポートによる復旧方法を確認した
- [ ] 元SQLiteと移行ログを安全な場所へ保管した

## 6. 復旧と秘密情報

ローカルデモは `backup/` にSQLiteバックアップを作ります。本番Supabaseは契約プランのDatabase Backups/PITR設定を確認してください。加えて月次CSV・Excelを暗号化された保管先へ保存してください。service-role key、Google Client secret、実値入りSecretsはGitへ登録しません。設定項目の一覧は [本番環境用設定一覧.md](本番環境用設定一覧.md) を参照してください。

## 7. 外部資格情報がない環境で確認できないこと

実Googleログイン、実Calendar応答、実Supabase RLS・RPC、Community CloudのHTTPS公開は、利用者所有のプロジェクトと認証情報が必要です。コードはデモモードと自動テストで確認し、本番環境では上記チェックリストに沿って最終受入確認を行ってください。

