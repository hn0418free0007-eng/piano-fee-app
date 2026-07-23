# PROJECT STATUS

## 最終更新日

2026-07-23（「今日の受付」画面の本日の受領額DB化を実装）

## 現在の状態

- システム名: ピアノ教室運営アプリ Ver.3
- Repository: `piano-fee-app`
- 本番ブランチ: `main`
- Streamlit起動ファイル: `local_web_app/app.py`
- GitHub、Streamlit Community Cloud、Supabase、Google OAuth、Google Calendar APIの接続は完了しています。
- Google Calendar予定の取得、生徒照合、9,000円の受領登録まで本番相当環境で確認済みです。
- Identity Sequence自動同期は、コミット `11ec903`（2026-07-23 14:45、`Add Supabase identity sequence synchronization`）で反映済みです。関連テスト（`test_migrate_to_supabase.py`）4件が成功しています。
- `main` は `origin/main` より進んでいます（pushはユーザーの明示的な指示があるまで行いません）。
- 売上管理・確定申告画面が40,000円と表示される問題は、「請求月ベース（target_month）」と「受領日ベース（received_date）」を区別せず合算していたことが原因と特定し、両基準を明示的に切り替えられるよう`services/sales_service.py`・`pages/sales.py`を修正しました。詳細は下記「既知の問題」を参照してください。
- 「今日の受付」画面の「今日の売上」（ブラウザセッション限定の`st.session_state`集計）を、DBの`received_date`基準の「本日の受領額」に変更しました（`services/sales_service.py`の`daily_received_amount()`/`today_received_amount()`、`Asia/Tokyo`基準）。全テストスイートは23件成功しています。
- 実装過程で、クラウド経路の`complete_lesson_payment` RPCが`received_date`をPostgresの`current_date`デフォルト（DBサーバーのタイムゾーン）に委ねており、JSTの実際の日付とずれる可能性がある根本的な課題が残っていることを確認しました。本番の中核トランザクションRPCへの変更となり本番でしか検証できないため、今回は実装せず別タスクとして保留しています（詳細は下記「既知の問題」）。

## 次回最優先

次回は、必ず次の順序で進めます。

1. `docs/08_CHATGPT引継ぎ.md` と本ファイル、`docs/worklog.md` の最新エントリを読む。
2. 本番Supabaseで `show timezone;` を実行し、DBのタイムゾーン設定を確認する（`complete_lesson_payment` RPCの`received_date`問題の前提確認）。
3. Streamlit本番環境でログイン、Calendar取得、今日の受付（本日の受領額の表示）、受領登録、売上管理画面（請求月別／受領月別の切替）を確認する。
4. 本番Supabaseで、確認用SQL（下記「既知の問題」参照）を実行し、実データでの40,000円内訳（22,000円＋18,000円）が今回の原因（前受金・後払いの混入）と一致するか最終確認する。
5. `complete_lesson_payment` RPCの`received_date`をJST対応させるかどうかをユーザーと決定する（対応する場合は限定的な修正案を参照）。
6. 受領取消処理を確認する（`payments` 物理削除なし、`cancelled_at`・取消理由保存、`charges` 状態復帰、`audit_logs` 記録）。
7. 保留事項（CSV/Excel出力への請求月基準追加、`services/dashboard_service.py`のクラウド対応）の対応要否を検討する。
8. 作業終了前に本ファイルと `docs/08_CHATGPT引継ぎ.md`、`docs/worklog.md` を更新する。

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
- [x] Identity Sequence同期の実装・コミット（`11ec903`）
- [x] 受領登録時のduplicate keyエラー対策
- [x] プロジェクトドキュメント8ファイルの作成
- [x] `docs/` のGitHubへのpush
- [x] ローカルデモモードと自動テスト
- [x] 売上40,000円問題の原因特定・修正（請求月ベース／受領日ベースの分離。ローカル・UIで解消を確認済み、本番実データでの最終確認は次回）
- [x] 作業履歴管理（`docs/worklog.md`）の運用開始
- [x] 「今日の受付」画面の「本日の受領額」DB化（`daily_received_amount()`/`today_received_amount()`、Asia/Tokyo基準、新規RPC無し）

## 動作確認済み

- [x] Google Calendarの予定を取得できる
- [x] Calendar予定から生徒を照合できる
- [x] 9,000円の受領登録ができる
- [x] 受領後に今日の売上が9,000円になる
- [x] 受領後に受領済み1名になる
- [x] 受領後に未受領0名になる
- [x] Identity Sequence同期テスト4件が成功する
- [x] 全体テストスイート23件が成功する（Identity Sequence関連含む既存14件＋本日の受領額テスト9件）
- [x] Streamlit AppTestで売上管理画面の集計基準切替（請求月別⇄受領月別）を確認する
- [x] Streamlit AppTestで「本日の受領額」が受領登録前0円→登録後実額へ更新されることを確認する

## 未完了

- [ ] 本番Supabase実データでの40,000円内訳の最終確認
- [ ] CSV/Excel出力（`export_service.dataset()`）へ請求月基準の出力を追加するかどうかの検討
- [ ] `services/dashboard_service.py`のSupabaseクラウド対応（現状デッドコードのため緊急ではない）
- [ ] `complete_lesson_payment` RPCの`received_date`をJST基準で明示する対応（別タスク、本番DBタイムゾーン確認が前提）
- [ ] 受領取消処理の動作確認
- [ ] Excel出力の確認・改善（売上以外の出力項目）
- [ ] 本番データでの総合運用テスト
- [ ] `docs/01_URL一覧.md` の未設定になっている本番URL・Project名の追記
- [ ] Streamlit本番環境でのブラウザ確認

## 既知の問題

### 売上管理・確定申告画面が40,000円（コード対応済み・本番実データでの最終確認待ち）

#### 原因（特定済み）

`services/sales_service.py` の集計関数はいずれも、対象月の判定を `received_date`（受領日）の年月だけで行っており、`target_month`（その入金がどの請求月に対するものか）を無視して合算していました。前受金（翌月分を当月中に受領）や後払い（過去分を当月にまとめて受領）があると、実際の請求額より多く表示されます。ローカルデモDBで再現し、本番報告の「22,000円」という内訳と数値的に一致する構造であることを確認済みです（再現条件・SQLは `docs/worklog.md` の2026-07-23エントリを参照）。

#### 対応内容

「請求月ベース（target_month）」と「受領日ベース（received_date）」を統一せず、明確に区別して両方確認できるようにしました。

- `services/sales_service.py`: `monthly_sales`→`monthly_billed_amount`（請求月基準）／`monthly_received_amount`（受領月基準）に分割。`yearly_sales`・`student_yearly_sales`も同様に分割。`recital_sales`は`recital_billed_amount`に改名（発表会費は開催＝target_month基準のまま、ロジック変更なし）。
- `pages/sales.py`: 「月別集計」「年間集計」「生徒別年間集計」タブに集計基準（請求月別／受領月別）を切り替えるラジオボタンとキャプションを追加。
- `services/export_service.py` / `pages/reports.py`: 管理画面のCSV/Excel出力（`受領月別一覧（受領日基準）`等）は受領日基準であることを列名・選択肢名で明示（ロジックは未変更、target_month基準の出力追加は保留）。
- テスト: 6月分後払い・7月分通常・8月分前払いの3パターンを検証する回帰テストを追加（`tests/test_sales_service.py`）。全14テストが成功。Streamlit AppTestでも、同一データで請求月基準10,000円／受領月基準30,000円と正しく切り替わることを確認済み。

#### 本番Supabase実データでの最終確認（未実施）

本番Supabaseには直接アクセスできる認証情報がこの開発環境に無いため、40,000円（22,000円＋18,000円）の実データ内訳は未確認です。次回、Supabase SQL Editorで次のSQLを実行して確認してください。

```sql
select
  student_name, payment_type, target_month,
  to_char(received_date,'YYYY-MM') as received_month,
  amount_received, received_date, cancelled_at
from public.payments
where cancelled_at is null
  and to_char(received_date,'YYYY-MM') = '対象年月'
order by student_name, received_date;
```

#### 保留とした対応（別タスク）

- CSV/Excel出力（`export_service.dataset()`）へ請求月基準の出力を追加するかどうか。
- `services/dashboard_service.py`のクラウド対応（現状デッドコードのため緊急ではない）。

### 「今日の受付」画面の「本日の受領額」DB化（対応済み）

「今日の受付」画面の「今日の売上」は、ブラウザセッション中の`st.session_state`だけを合算しており、DBを参照していませんでした（再読み込み・別端末で値が消える／一致しない）。`services/sales_service.py`に`daily_received_amount(day=None)`（`day`省略時は`Asia/Tokyo`基準の当日）と`today_received_amount()`を追加し、`pages/v3_today.py`のメトリクスをDB参照（`received_date`が対象日、`cancelled_at is null`の`amount_received`合計）に変更しました。新規RPCは作成せず、クラウド時はDB側で`received_date`・`cancelled_at`を絞り込んでから合計する方式です。テスト9件を追加し、全23テストが成功しています。

流用を避けた`services/dashboard_service.py`はSupabaseクラウド非対応（`is_cloud_configured()`分岐が無くローカルSQLite固定）であり、加えて`pages/dashboard.py`・`reports.render_daily()`は現在`app.py`から呼ばれていないデッドコードです（変更していません）。

### complete_lesson_payment RPCのreceived_dateタイムゾーン問題（未対応・別タスク）

「本日の受領額」の集計はJST基準にしましたが、**登録側**の`complete_lesson_payment` RPC（クラウド「今日の受付」の受領登録経路）は、INSERT文に`received_date`列を含めておらず、テーブル定義の`default current_date`（Postgresサーバーのセッションタイムゾーン。Supabaseは新規プロジェクトで既定UTCのことが多い）に委ねたままです。

- JST 00:00〜08:59（UTCではまだ前日）に受領登録すると、`received_date`がJSTの実際の日付より1日前で記録される可能性があります。この場合、登録直後の「本日の受領額」には反映されず、月をまたぐ場合は月次集計（`monthly_received_amount`等）にもズレが波及します。
- 修正が必要と判断しますが、**今回は実装していません**。理由: `complete_lesson_payment`は本番で最も頻繁に実行される受領登録の中核トランザクションRPCであり、変更には本番Supabaseへの新規SQLマイグレーション適用（SQL Editorでの手動実行）が必要で、この開発環境からは実行・検証ができないためです。
- 対応する場合は、RPCに`p_received_date`パラメータを追加し、Python側（`v3_repository.complete()`のクラウド分岐）で`Asia/Tokyo`基準の日付を明示的に渡す「限定的な修正」を推奨します（データベース全体のタイムゾーン設定を変更する方法は、`created_at`等の他カラムにも影響するため推奨しません）。
- まず本番Supabaseで `show timezone;` を実行し、既に`Asia/Tokyo`に設定済みでないか確認してください。

### Identity Sequence同期

コミット `11ec903`（2026-07-23）で対応済みです。対象は `students`、`charges`、`payments`、`audit_logs` の4テーブルです。関連テスト4件が成功しています。

## 現在のGit状態

- ドキュメント整合性修正: コミット `15c0b2b`（`Sync docs with actual git state and start worklog`）
- 売上集計の請求月／受領日基準分離、および「本日の受領額」DB化: それぞれ別コミットとして反映済み（正確なコミットIDは `git log --oneline` で確認してください）
- `main` はこの時点で `origin/main` へは未pushです（pushはユーザーの明示的な指示があるまで行いません）。
- 未コミットの変更が無いことは、作業終了時に必ず `git status` で確認してください。

## 次回の作業順序

### 1. 引継ぎ資料を読む

- `docs/08_CHATGPT引継ぎ.md`
- `docs/04_PROJECT_STATUS.md`
- `docs/worklog.md`（最新エントリ）

### 2. 本番SupabaseのDBタイムゾーンを確認する

`show timezone;` をSQL Editorで実行し、`complete_lesson_payment` RPCの`received_date`問題の前提を確認する。

### 3. Streamlit本番確認

- 正常起動
- Googleログイン
- Calendar取得
- 今日の受付表示（「本日の受領額」が正しく表示されること）
- 受領登録
- 売上管理・確定申告画面（請求月別／受領月別の切替）の表示が正しいこと
- エラーがない

### 4. 本番Supabaseで40,000円問題の実データを最終確認する

上記「既知の問題」に記載の確認用SQLを実行し、内訳（22,000円＋18,000円）が前受金・後払いの混入によるものかを確認する。

### 5. complete_lesson_payment RPCのreceived_date対応を判断する

本番DBタイムゾーンの確認結果を踏まえ、対応するかどうか、対応する場合は限定的な修正案（RPCへのJST日付パラメータ追加）で進めるかをユーザーと決定する。

### 6. 受領取消処理を確認する

- `payments` を物理削除しない
- `cancelled_at` と取消理由が保存される
- `charges` が未受領相当へ戻る
- 受領済み人数と売上から除外される
- `audit_logs` に履歴が残る

### 7. 保留事項を検討する

- CSV/Excel出力への請求月基準追加
- `services/dashboard_service.py`のクラウド対応

### 8. 文書を更新する

本ファイル、`docs/08_CHATGPT引継ぎ.md`、`docs/worklog.md` を必ず最新化します。

## 直近のコミット

| コミット | メッセージ | 内容 |
|---|---|---|
| （直近） | `Add DB-backed today's received amount` 等 | 「本日の受領額」DB化、テスト追加（正確なメッセージ・IDは `git log` を参照） |
| `8629d84` | `Split sales aggregation into billed-month and received-month bases` | 売上集計の請求月／受領日基準分離、テスト追加 |
| `15c0b2b` | `Sync docs with actual git state and start worklog` | ドキュメントをGit実態に同期、`docs/worklog.md`運用開始 |
| `11ec903` | `Add Supabase identity sequence synchronization` | Identity Sequence自動同期を実装・コミット |
| `620128c` | `Update README with project documentation guide` | README整理 |
| `415610d` | `Add release notes` | リリースノート追加 |
| `c1b45c8` | `Update project handoff and next steps` | 引継ぎ資料更新 |
| `00983e8` | `Add project documentation` | `docs/` の8ファイルを追加してpush |

## 更新履歴

人が読みやすいリリース単位の変更履歴は `docs/09_リリースノート.md` を参照してください。

| 日付 | 変更内容 | 状態 |
|---|---|---|
| 2026-07-23 | 「今日の受付」画面の「今日の売上」（session_state集計）をDBの`received_date`基準「本日の受領額」に変更。`services/sales_service.py`に`daily_received_amount()`/`today_received_amount()`（Asia/Tokyo基準、新規RPC無し）を追加。テスト9件追加で全23テスト成功。`complete_lesson_payment` RPCの`received_date`がPostgresの`current_date`任せでJST非対応である根本課題を発見し、本番トランザクションRPCへの変更は影響が大きいため別タスクとして保留 | 完了（RPCのreceived_date対応は別タスク） |
| 2026-07-23 | 売上40,000円問題を修正。`services/sales_service.py`を請求月基準／受領日基準の関数に分割し、`pages/sales.py`に集計基準の切替UIを追加。前受金・後払いの回帰テストを追加し全14テスト成功。CSV/Excel出力（`export_service.py`）は受領日基準である旨を明示。「今日の受付」画面の受領額DB化と`dashboard_service.py`のクラウド対応は別タスクとして保留 | 完了（本番実データでの最終確認は次回） |
| 2026-07-23 | Identity Sequence変更がコミット済みであることを反映し、テスト結果（4件・全体12件成功）を記録。売上40,000円問題の原因をコードレベルで特定（`received_date`基準集計と`target_month`の不一致）。作業履歴管理（`docs/worklog.md`）の運用を開始 | 完了 |
| 2026-07-17 | 現在のGit状態、動作確認済み内容、40,000円問題、次回8段階手順を追記 | 完了 |
| 2026-07-17 | プロジェクトドキュメント8ファイルを作成しGitHubへpush | 完了 |
| 2026-07-17 | Identity Sequence同期を実装 | 完了（2026-07-23コミット済み） |
| 2026-07-17 | PKCE verifier永続化を実装・push | 完了 |

更新時は、新しい行を表の先頭へ追加してください。
