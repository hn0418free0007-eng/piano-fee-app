-- 既存SupabaseプロジェクトへIdentityシーケンス同期RPCだけを追加する。
create or replace function sync_migration_identity_sequences()
returns table(table_name text,column_name text,max_id bigint,sequence_value bigint,is_called boolean)
language plpgsql
security definer
set search_path = ''
as $$
declare
 v_table text; v_column text; v_sequence text; v_max bigint; v_has_rows boolean;
begin
 lock table public.students,public.charges,public.payments,public.audit_logs in access exclusive mode;
 for v_table,v_column in
  select * from (values
   ('public.students','student_id'),('public.charges','charge_id'),
   ('public.payments','payment_id'),('public.audit_logs','log_id')
  ) as identity_columns(table_name,column_name)
 loop
  v_sequence:=pg_catalog.pg_get_serial_sequence(v_table,v_column);
  if v_sequence is null then raise exception 'Identity sequence not found for %.%',v_table,v_column; end if;
  execute pg_catalog.format('select max(%I),count(*)>0 from %s',v_column,v_table::regclass)
   into v_max,v_has_rows;
  perform pg_catalog.setval(v_sequence::regclass,coalesce(v_max,1),v_has_rows);
  table_name:=pg_catalog.split_part(v_table,'.',2); column_name:=v_column;
  max_id:=v_max; sequence_value:=coalesce(v_max,1); is_called:=v_has_rows;
  return next;
 end loop;
end $$;
revoke all on function sync_migration_identity_sequences() from public;
grant execute on function sync_migration_identity_sequences() to service_role;

-- すでにID付き移行が完了している既存プロジェクトも、このSQL実行時に直ちに同期する。
select * from sync_migration_identity_sequences();
