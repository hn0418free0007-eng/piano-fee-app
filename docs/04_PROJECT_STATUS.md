# PROJECT STATUS

## 最終更新日

2026-07-23（売上集計の請求月／受領日基準分離を実装）

## 現在の状態

- システム名: ピアノ教室運営アプリ Ver.3
- Repository: `piano-fee-app`
- 本番ブランチ: `main`
- Streamlit起動ファイル: `local_web_app/app.py`
- GitHub、Streamlit Community Cloud、Supabase、Google OAuth、Google Calendar APIの接続は完了しています。
- Google Calendar予定の取得、生徒照合、9,000円の受領登録まで本番相当環境で確認済みです。
- Identity Sequence自動同期は、コミット `11ec903`（2026-07-23 14:45、`Add Supabase identity sequence synchronization`）で反映済みです。関連テスト（`test_migrate_to_supabase.py`）4件、全体テスト12件がすべて成功しています。
- `git status` はクリーンで、`main` は `origin/main` と同期済みです。
- 売上管理・確定申告画面が40,000円と表示される問題は、「請求月ベース（target_month）」と「受領日ベース（received_date）」を区別せず合算していたことが原因と特定し、両基準を明示的に切り替えられるよう`services/sales_service.py`・`pages/sales.py`を修正しました。全14テストが成功しています。詳細は下記「既知の問題」を参照してください。

## 次回最優先

次回は、必ず次の順序で進めます。

1. `docs/08_CHATGPT引継ぎ.md` と本ファイル、`docs/worklog.md` の最新エントリを読む。
2. Streamlit本番環境でログイン、Calendar取得、今日の受付、受領登録、売上管理画面（請求月別／受領月別の切替）を確認する。
3. 本番Supabaseで、確認用SQL（下記「既知の問題」参照）を実行し、実データでの40,000円内訳（22,000円＋18,000円）が今回の原因（前受金・後払いの混入）と一致するか最終確認する。
4. 受領取消処理を確認する（`payments` 物理削除なし、`cancelled_at`・取消理由保存、`charges` 状態復帰、`audit_logs` 記録）。
5. 保留事項（CSV/Excel出力への請求月基準追加、「今日の受付」画面の受領額DB化、`services/dashboard_service.py`のクラウド対応）の対応要否を検討する。
6. 作業終了前に本ファイルと `docs/08_CHATGPT引継ぎ.md`、`docs/worklog.md` を更新する。

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

## 動作確認済み

- [x] Google Calendarの予定を取得できる
- [x] Calendar予定から生徒を照合できる
- [x] 9,000円の受領登録ができる
- [x] 受領後に今日の売上が9,000円になる
- [x] 受領後に受領済み1名になる
- [x] 受領後に未受領0名になる
- [x] Identity Sequence同期テスト4件が成功する
- [x] 全体テストスイート14件が成功する（既存12件＋売上集計の前受金・後払いテスト2件）
- [x] Streamlit AppTestで売上管理画面の集計基準切替（請求月別⇄受領月別）を確認する

## 未完了

- [ ] 本番Supabase実データでの40,000円内訳の最終確認
- [ ] CSV/Excel出力（`export_service.dataset()`）へ請求月基準の出力を追加するかどうかの検討
- [ ] 「今日の受付」画面の「今日の売上」をDBの受領日基準へ変更する対応（別タスク）
- [ ] `services/dashboard_service.py`のSupabaseクラウド対応（現状デッドコードのため緊急ではない）
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
- 「今日の受付」画面（`pages/v3_today.py`）の「今日の売上」は、現在ブラウザセッション中の`st.session_state`だけを合算しており、DBを参照していません。DBの`received_date`基準に変更する案は影響分析のみ実施し、実装は見送りました。理由: 既存の`services/dashboard_service.py`（`today_amount`等）がSupabaseクラウド非対応（`is_cloud_configured()`分岐が無くローカルSQLite固定）であり、単純な流用ができないためです。加えて`pages/dashboard.py`・`reports.render_daily()`は現在`app.py`から呼ばれていないデッドコードであることも判明しました。
- `services/dashboard_service.py`のクラウド対応（現状デッドコードのため緊急ではない）。

### Identity Sequence同期

コミット `11ec903`（2026-07-23）で対応済みです。対象は `students`、`charges`、`payments`、`audit_logs` の4テーブルです。関連テスト4件が成功しています。

## 現在のGit状態

- ドキュメント整合性修正: コミット `15c0b2b`（`Sync docs with actual git state and start worklog`）
- 売上集計の請求月／受領日基準分離: 直後の別コミットとして反映済み（正確なコミットIDは `git log -1 --oneline` で確認してください）
- `main` はこの時点で `origin/main` へは未pushです（pushはユーザーの明示的な指示があるまで行いません）。
- 未コミットの変更が無いことは、作業終了時に必ず `git status` で確認してください。

## 次回の作業順序

### 1. 引継ぎ資料を読む

- `docs/08_CHATGPT引継ぎ.md`
- `docs/04_PROJECT_STATUS.md`
- `docs/worklog.md`（最新エントリ）

### 2. Streamlit本番確認

- 正常起動
- Googleログイン
- Calendar取得
- 今日の受付表示
- 受領登録
- 売上管理・確定申告画面（請求月別／受領月別の切替）の表示が正しいこと
- エラーがない

### 3. 本番Supabaseで40,000円問題の実データを最終確認する

上記「既知の問題」に記載の確認用SQLを実行し、内訳（22,000円＋18,000円）が前受金・後払いの混入によるものかを確認する。

### 4. 受領取消処理を確認する

- `payments` を物理削除しない
- `cancelled_at` と取消理由が保存される
- `charges` が未受領相当へ戻る
- 受領済み人数と売上から除外される
- `audit_logs` に履歴が残る

### 5. 保留事項を検討する

- CSV/Excel出力への請求月基準追加
- 「今日の受付」画面の受領額DB化
- `services/dashboard_service.py`のクラウド対応

### 6. 文書を更新する

本ファイル、`docs/08_CHATGPT引継ぎ.md`、`docs/worklog.md` を必ず最新化します。

## 直近のコミット

| コミット | メッセージ | 内容 |
|---|---|---|
| （直近） | `Split sales aggregation into billed/received amount` 等 | 売上集計の請求月／受領日基準分離、テスト追加（正確なメッセージ・IDは `git log` を参照） |
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
| 2026-07-23 | 売上40,000円問題を修正。`services/sales_service.py`を請求月基準／受領日基準の関数に分割し、`pages/sales.py`に集計基準の切替UIを追加。前受金・後払いの回帰テストを追加し全14テスト成功。CSV/Excel出力（`export_service.py`）は受領日基準である旨を明示。「今日の受付」画面の受領額DB化と`dashboard_service.py`のクラウド対応は別タスクとして保留 | 完了（本番実データでの最終確認は次回） |
| 2026-07-23 | Identity Sequence変更がコミット済みであることを反映し、テスト結果（4件・全体12件成功）を記録。売上40,000円問題の原因をコードレベルで特定（`received_date`基準集計と`target_month`の不一致）。作業履歴管理（`docs/worklog.md`）の運用を開始 | 完了 |
| 2026-07-17 | 現在のGit状態、動作確認済み内容、40,000円問題、次回8段階手順を追記 | 完了 |
| 2026-07-17 | プロジェクトドキュメント8ファイルを作成しGitHubへpush | 完了 |
| 2026-07-17 | Identity Sequence同期を実装 | 完了（2026-07-23コミット済み） |
| 2026-07-17 | PKCE verifier永続化を実装・push | 完了 |

更新時は、新しい行を表の先頭へ追加してください。
