from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _read(name):
    return (ROOT / name).read_text(encoding='utf-8')

def test_migration_sql_documents_purpose_and_background():
    sql = _read('supabase_received_date_jst_fix.sql')
    assert 'Purpose' in sql
    assert 'Background' in sql

def test_migration_sql_drops_old_signature_before_creating_new_one():
    sql = _read('supabase_received_date_jst_fix.sql')
    drop_pos = sql.index('drop function if exists complete_lesson_payment(bigint,text,text,text)')
    create_pos = sql.index('create or replace function complete_lesson_payment')
    assert drop_pos < create_pos  # 旧版を先に削除してから新版を作成する

def test_migration_sql_wraps_drop_and_create_in_a_single_transaction():
    sql = _read('supabase_received_date_jst_fix.sql')
    begin_pos = sql.index('begin;')
    drop_pos = sql.index('drop function if exists complete_lesson_payment(bigint,text,text,text)')
    create_end_pos = sql.index('end $$;')
    commit_pos = sql.index('commit;')
    # DROPとCREATEが同一トランザクション内にあり、CREATE失敗時はDROPごとロールバックされる
    assert begin_pos < drop_pos < create_end_pos < commit_pos

def test_migration_sql_uses_jst_date_with_fallback_and_keeps_security_invoker():
    sql = _read('supabase_received_date_jst_fix.sql')
    assert 'p_received_date date default null' in sql
    assert 'coalesce(p_received_date,current_date)' in sql
    assert 'security invoker' in sql
    assert 'security definer' not in sql

def test_schema_sql_complete_lesson_payment_has_single_definition_with_received_date():
    sql = _read('supabase_schema.sql')
    assert sql.count('create or replace function complete_lesson_payment') == 1
    assert 'p_received_date date default null' in sql
    assert 'coalesce(p_received_date,current_date)' in sql
