# PROJECT STATUS

## 最終更新日

2026-07-23

## 現在の状態

- システム名: ピアノ教室運営アプリ Ver.3
- Repository: `piano-fee-app`
- 本番ブランチ: `main`
- Streamlit起動ファイル: `local_web_app/app.py`
- GitHub、Streamlit Community Cloud、Supabase、Google OAuth、Google Calendar APIの接続は完了しています。
- Google Calendar予定の取得、生徒照合、9,000円の受領登録まで本番相当環境で確認済みです。
- Identity Sequence自動同期は、コミット `11ec903`（2026-07-23 14:45、`Add Supabase identity sequence synchronization`）で反映済みです。関連テスト（`test_migrate_to_supabase.py`）4件、全体テスト12件がすべて成功しています。
- `git status` はクリーンで、`main` は `origin/main` と同期済みです。
- 売上管理・確定申告画面が40,000円と表示される問題は、原因をコードレベルで特定しました（詳細は下記「既知の問題」）。修正はまだ適用していません。承認待ちです。

## 次回最優先

次回は、必ず次の順序で進めます。

1. `docs/08_CHATGPT引継ぎ.md` と本ファイルを読む。
2. 売上集計ロジック（`services/sales_service.py`）の修正方針についてユーザーの承認を得る。
3. 承認後、`monthly_sales`・`yearly_sales`・`student_yearly_sales`・`recital_sales` の集計基準（`received_date` と `target_month` の扱い）を修正する。
4. 修正後、既存テストに加えて売上集計の回帰テストを追加し、実行する。
5. `git status`・`git diff` を確認し、対象ファイルだけをコミットする。
6. Streamlit本番環境でログイン、Calendar取得、今日の受付、受領登録、売上管理画面を確認する。
7. 受領取消処理を確認する（`payments` 物理削除なし、`cancelled_at`・取消理由保存、`charges` 状態復帰、`audit_logs` 記録）。
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
- [x] 売上40,000円問題の原因特定（コードレベル、修正は未適用）
- [x] 作業履歴管理（`docs/worklog.md`）の運用開始

## 動作確認済み

- [x] Google Calendarの予定を取得できる
- [x] Calendar予定から生徒を照合できる
- [x] 9,000円の受領登録ができる
- [x] 受領後に今日の売上が9,000円になる
- [x] 受領後に受領済み1名になる
- [x] 受領後に未受領0名になる
- [x] Identity Sequence同期テスト4件が成功する
- [x] 全体テストスイート12件が成功する

## 未完了

- [ ] 売上管理・確定申告画面の集計ロジック修正（原因特定済み、修正方針は承認待ち）
- [ ] 受領取消処理の動作確認
- [ ] CSV出力の確認・改善
- [ ] Excel出力の確認・改善
- [ ] 本番データでの総合運用テスト
- [ ] `docs/01_URL一覧.md` の未設定になっている本番URL・Project名の追記
- [ ] Streamlit本番環境でのブラウザ確認（売上問題の修正方針確定後に実施）

## 既知の問題

### 売上管理・確定申告画面が40,000円（原因特定済み・修正未適用）

#### 確認済みの事実

- 9,000円の受領登録自体は正常です。
- 今日の受付画面（`pages/v3_today.py`）の「今日の売上」は、その日その画面が開かれているブラウザセッション中に「受領・押印済み」を押した分だけを `st.session_state` 上で合算した値であり、データベースへの問い合わせは行っていません。ページを再読み込みすると0に戻ります。
- 売上管理・確定申告画面（`pages/sales.py` → `services/sales_service.py`）の「月別売上」は、`payments` テーブルから `cancelled_at is null` の行を全件取得し、**`received_date`（実際に受領した日）の年月**が対象年月と一致する行を合算します。**`target_month`（請求対象月）では絞り込んでいません。**
- そのため、「今日の受付」で見えている9,000円（＝今回の1件）と、「月別売上」に出る合計額（同じ暦月に受領された全ての入金の合計）は、そもそも比較対象が異なります。

#### 再現による根拠

ローカルデモDB（`local_web_app/data/lesson_fee.db`）には、次の3件の入金が登録されています。

| payment_id | 生徒 | target_month（請求対象月） | received_date（受領日） | amount_received |
|---|---|---|---|---|
| 1 | あおぞら かなで | 2026-07 | 2026-07-16 | 11,000 |
| 2 | さくら みらい | 2026-07 | 2026-07-16 | 9,000 |
| 3 | あおぞら かなで | **2026-08** | 2026-07-16 | 11,000 |

`monthly_sales('2026-07')` を実行すると、次の結果になります（実際に実行して確認済み）。

```text
{'生徒名': 'あおぞら かなで', '請求種別': '月謝', '売上金額': 22000}
{'生徒名': 'さくら みらい', '請求種別': '月謝', '売上金額': 9000}
```

「あおぞら かなで」の7月分の請求は本来11,000円ですが、8月分の請求（payment_id 3）を7月中に前払いで受領しているため、`received_date` 基準の集計では7月の売上に22,000円（11,000円×2件）として合算されています。本番で報告されている「22,000円」という内訳の数字は、この仕組みと一致します。

#### 原因

`services/sales_service.py` の `monthly_sales` / `yearly_sales` / `student_yearly_sales` / `recital_sales` はいずれも、対象月の判定を `received_date` の年月で行っており、`target_month`（その入金がどの請求月・請求種別に対するものか）を無視して合算しています。このため、次のようなケースで実際の請求額より多く表示されます。

- 前受金（翌月分の月謝を当月中に受領した場合）
- 過去分の未収金を当月にまとめて受領した場合（催促・後払いの回収）
- 開発・確認作業中に生成された複数回のテスト入金が、取消されないまま同一暦月に残っている場合

#### 本番の40,000円（22,000円＋18,000円）について

本番のSupabaseデータには直接アクセスできる認証情報がこの開発環境に無いため、実データでの内訳は未確認です。ただし、上記の再現結果は本番で報告された内訳の一部（22,000円）と数値的に一致する構造であり、同じ仕組み（前受金・後払い・未取消のテスト入金が `received_date` 基準の月次集計に混入する）が原因である可能性が高いと判断します。

本番データでの最終確認には、次のSQLをSupabase SQL Editorで実行し、`received_date` の月と `target_month` が一致しない行、または同一生徒・同一 `payment_type` で複数件存在する行を洗い出す必要があります。

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

#### 修正方針（未適用・承認待ち）

- 集計基準を `target_month` にするか、`received_date` にするか、または両方を併記して区別できるようにするか、運用上どちらが正しい「売上」の定義か確認してから修正する。
- 修正後は、前受金・後払いケースを含む回帰テストを追加する。
- 既存の確定申告・CSV/Excel出力など、`sales_service.py` を参照する画面全てへの影響を確認する。

### Identity Sequence同期

コミット `11ec903`（2026-07-23）で対応済みです。対象は `students`、`charges`、`payments`、`audit_logs` の4テーブルです。関連テスト4件が成功しています。

## 現在のGit状態

- `git status`: クリーン（`nothing to commit`）
- `main` は `origin/main` と同期済みです。
- 最新コミット: `11ec903131cc1368e5e1759b13fe0a83f5be8911`（`Add Supabase identity sequence synchronization`、2026-07-23 14:45）

未コミットの変更はありません。ドキュメント更新・売上原因調査は、この時点ではまだユーザーの承認待ちのためコミットしていません。

## 次回の作業順序

### 1. 引継ぎ資料を読む

- `docs/08_CHATGPT引継ぎ.md`
- `docs/04_PROJECT_STATUS.md`
- `docs/worklog.md`（最新エントリ）

### 2. 売上集計修正の承認を得る

上記「既知の問題」の修正方針についてユーザーの判断を仰ぐ。承認前にコードを変更しない。

### 3. 修正・テスト

承認された方針で `services/sales_service.py` を修正し、回帰テストを追加・実行する。

### 4. コミット

```powershell
git status
git diff
git add <対象ファイル>
git diff --cached
git commit -m "<内容に応じたメッセージ>"
git push origin main
git status
```

### 5. Streamlit本番確認

- 正常起動
- Googleログイン
- Calendar取得
- 今日の受付表示
- 受領登録
- 売上管理・確定申告画面の表示が正しいこと
- エラーがない

### 6. 受領取消処理を確認する

- `payments` を物理削除しない
- `cancelled_at` と取消理由が保存される
- `charges` が未受領相当へ戻る
- 受領済み人数と売上から除外される
- `audit_logs` に履歴が残る

### 7. 文書を更新する

本ファイル、`docs/08_CHATGPT引継ぎ.md`、`docs/worklog.md` を必ず最新化します。

## 直近のコミット

| コミット | メッセージ | 内容 |
|---|---|---|
| `11ec903` | `Add Supabase identity sequence synchronization` | Identity Sequence自動同期を実装・コミット |
| `620128c` | `Update README with project documentation guide` | README整理 |
| `415610d` | `Add release notes` | リリースノート追加 |
| `c1b45c8` | `Update project handoff and next steps` | 引継ぎ資料更新 |
| `00983e8` | `Add project documentation` | `docs/` の8ファイルを追加してpush |

## 更新履歴

人が読みやすいリリース単位の変更履歴は `docs/09_リリースノート.md` を参照してください。

| 日付 | 変更内容 | 状態 |
|---|---|---|
| 2026-07-23 | Identity Sequence変更がコミット済みであることを反映し、テスト結果（4件・全体12件成功）を記録。売上40,000円問題の原因をコードレベルで特定（`received_date`基準集計と`target_month`の不一致）。作業履歴管理（`docs/worklog.md`）の運用を開始 | 完了 |
| 2026-07-17 | 現在のGit状態、動作確認済み内容、40,000円問題、次回8段階手順を追記 | 完了 |
| 2026-07-17 | プロジェクトドキュメント8ファイルを作成しGitHubへpush | 完了 |
| 2026-07-17 | Identity Sequence同期を実装 | 完了（2026-07-23コミット済み） |
| 2026-07-17 | PKCE verifier永続化を実装・push | 完了 |

更新時は、新しい行を表の先頭へ追加してください。
