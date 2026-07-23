-- Purpose:
--   退会した生徒について「レッスン料を何月分まで請求するか」を保持する列を追加する。
--   保存形式は 'YYYY-MM'。未設定(NULL)は「先生が最終請求月をまだ決めていない／要確認」を意味し、
--   月次請求の対象判定では未設定の退会者を自動的に除外する（憶測で対象に含めない）。
--
-- Background:
--   これまでの月次請求(create_monthly)は enrollment_status='在籍' のみで対象者を判定しており、
--   退会日が月の途中でも、在籍状況を「退会」に変更した時点でその月の請求からも即座に除外されて
--   しまっていた。final_billing_month を導入し、「在籍状況」と「対象月がどこまで含まれるか」を
--   分離して判定できるようにする。
--
-- 影響範囲:
--   追加専用のNULL許容列で、既存の他カラム・他テーブルには影響しない。
--   既存の全生徒（在籍・退会問わず）は追加後もfinal_billing_month=NULLのまま。
--   withdrawal_date等からの自動補完は行わない（先生が画面で確認・入力する運用）。
--
-- 本番Supabaseへはまだ実行していない。アプリのデプロイと合わせて実行する。

alter table students add column if not exists final_billing_month text;

-- 適用後の確認（読み取り専用）: 列が追加され、既存行がすべてNULLであることを確認する。
-- select student_id,name,enrollment_status,withdrawal_date,final_billing_month
-- from public.students order by student_id;

-- ロールバックする場合（追加専用の列なので、他カラムへの影響なく安全に戻せる）:
-- alter table students drop column if exists final_billing_month;
