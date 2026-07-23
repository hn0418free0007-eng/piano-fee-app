-- Purpose:
--   complete_lesson_payment の payments.received_date が、Postgresの current_date
--   （DBサーバーのセッションタイムゾーン）にフォールバックされているのを、
--   呼び出し側（Python）でAsia/Tokyo基準に解決した日付を明示的に渡せるようにする。
--
-- Background:
--   本番Supabaseの database timezone は UTC。JST 00:00〜08:59（UTCではまだ前日）に
--   「受領・押印済み」を押すと、payments.received_date がJSTの実際の日付より
--   1日前で記録される可能性がある。集計側（services/sales_service.py の
--   daily_received_amount 等）はAsia/Tokyo基準に対応済みだが、登録側（このRPC）が
--   未対応のままだと根本原因が残る。
--
--   今回は後方互換のための旧シグネチャ温存は行わず、RPCは常に1つだけ存在する状態にする。
--   アプリと同時デプロイできるため、旧4引数版を先にDROPしてから新5引数版を作成する。
--   本番Supabase SQL Editorで、アプリのデプロイと合わせて実行する。
--   DROPとCREATEを同一トランザクションにまとめ、CREATEが失敗した場合はDROPごと
--   ロールバックされ、旧版が残るようにする（関数が存在しない状態を避ける）。

begin;

drop function if exists complete_lesson_payment(bigint,text,text,text);

create or replace function complete_lesson_payment(
 p_charge_id bigint,p_payment_method text,p_received_by text,p_calendar_event_id text default null,
 p_received_date date default null
) returns bigint language plpgsql security invoker as $$
declare c charges%rowtype; paid integer; remaining integer; new_id bigint;
begin
 select * into c from charges where charge_id=p_charge_id for update;
 if not found or c.charge_status in ('入金済','免除','取消') then raise exception 'この請求は登録できません'; end if;
 select coalesce(sum(amount_received),0) into paid from payments where charge_id=p_charge_id and cancelled_at is null;
 remaining:=c.charge_amount-paid;
 if remaining<=0 then raise exception 'この請求はすでに受領済みです'; end if;
 insert into payments(charge_id,student_id,student_name,target_month,payment_type,charge_amount,amount_received,
  received_date,payment_method,received_by,stamp_confirmed,stamp_confirmed_at,stamp_confirmed_by,payment_status,calendar_event_id)
 select c.charge_id,c.student_id,s.name,c.target_month,c.charge_type,c.charge_amount,remaining,
  coalesce(p_received_date,current_date),p_payment_method,p_received_by,true,now(),p_received_by,'処理完了',p_calendar_event_id from students s where s.student_id=c.student_id
 returning payment_id into new_id;
 update charges set charge_status='入金済',updated_at=now() where charge_id=c.charge_id;
 insert into audit_logs(action_type,target_table,target_id,student_id,action_detail,operator_name)
 values('受領・押印済み','payments',new_id,c.student_id,c.target_month||' '||c.charge_type||' '||remaining||'円',p_received_by);
 return new_id;
end $$;

commit;

-- 適用後の確認（読み取り専用）: complete_lesson_paymentが1つだけ存在し、5引数であることを確認する。
-- select proname, pg_get_function_identity_arguments(oid) from pg_proc where proname='complete_lesson_payment';
