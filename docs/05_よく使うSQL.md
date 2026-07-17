# よく使うSQL

## 目的

Supabase SQL Editorで使う確認・保守SQLです。実行前に対象Projectを必ず確認してください。

最終更新日: 2026-07-17

## 1. Identity Sequence同期

SQLiteから明示ID付きで移行した後に使います。通常は `local_web_app/supabase_sequence_sync.sql` を実行します。

```sql
select * from public.sync_migration_identity_sequences();
```

期待する対象:

- `students.student_id`
- `charges.charge_id`
- `payments.payment_id`
- `audit_logs.log_id`

## 2. Sequence状態確認

```sql
select 'students' as table_name, max(student_id) as max_id from public.students
union all
select 'charges', max(charge_id) from public.charges
union all
select 'payments', max(payment_id) from public.payments
union all
select 'audit_logs', max(log_id) from public.audit_logs;
```

```sql
select last_value, is_called from public.students_student_id_seq;
select last_value, is_called from public.charges_charge_id_seq;
select last_value, is_called from public.payments_payment_id_seq;
select last_value, is_called from public.audit_logs_log_id_seq;
```

## 3. 売上確認

取消されていない入金を月別に集計します。

```sql
select
  target_month,
  sum(amount_received) as sales_amount,
  count(*) as payment_count
from public.payments
where cancelled_at is null
group by target_month
order by target_month desc;
```

## 4. payments確認

```sql
select
  payment_id, charge_id, student_id, student_name,
  target_month, payment_type, amount_received,
  received_date, payment_method, payment_status,
  cancelled_at, cancellation_reason
from public.payments
order by payment_id desc
limit 100;
```

## 5. charges確認

```sql
select
  c.charge_id, c.student_id, s.name,
  c.target_month, c.charge_type, c.charge_amount,
  c.due_date, c.charge_status
from public.charges c
join public.students s on s.student_id = c.student_id
order by c.target_month desc, c.charge_id desc
limit 100;
```

## 6. students確認

```sql
select
  student_id, name, school_location, grade,
  monthly_fee, recital_fee, enrollment_status,
  enrollment_date, withdrawal_date
from public.students
order by student_id;
```

## 7. audit_logs確認

```sql
select
  log_id, action_datetime, action_type,
  target_table, target_id, student_id,
  action_detail, operator_name
from public.audit_logs
order by log_id desc
limit 200;
```

## 8. 許可された先生の確認

個人情報を含むため、結果を画面共有や文書へ転載しません。

```sql
select email, display_name, created_at
from public.allowed_teachers
order by created_at;
```

## 9. 動作確認SQL

請求と有効入金の合計を比較します。

```sql
select
  c.charge_id,
  s.name,
  c.target_month,
  c.charge_type,
  c.charge_amount,
  coalesce(sum(p.amount_received) filter (where p.cancelled_at is null), 0) as paid_amount,
  c.charge_status
from public.charges c
join public.students s on s.student_id = c.student_id
left join public.payments p on p.charge_id = c.charge_id
group by c.charge_id, s.name
order by c.charge_id desc;
```

重複Calendar処理候補を確認します。

```sql
select calendar_event_id, count(*)
from public.payments
where calendar_event_id is not null
  and cancelled_at is null
group by calendar_event_id
having count(*) > 1;
```

## 10. リセットSQL

危険: 以下はデータを削除します。本番では原則実行しません。対象がデモ専用Projectであること、バックアップがあること、利用者が停止していることを確認してください。

全業務データを削除する例:

```sql
begin;

truncate table
  public.audit_logs,
  public.payments,
  public.charges,
  public.calendar_mappings,
  public.students,
  public.migration_runs
restart identity cascade;

commit;
```

`allowed_teachers` はログイン不能を避けるため対象外です。途中で不安になった場合、`commit` 前に次を実行します。

```sql
rollback;
```

## SQL実行ルール

1. Project名を確認する
2. 最初はSELECTだけ実行する
3. UPDATE、DELETE、TRUNCATE、setvalはバックアップ後に実行する
4. 実行結果と日付を `04_PROJECT_STATUS.md` に記録する
5. Secretや実データをAIチャットへ貼らない
