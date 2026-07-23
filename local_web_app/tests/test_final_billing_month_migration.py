import sqlite3
import database

def _columns(con,table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}

def test_fresh_db_has_final_billing_month_column(tmp_path):
    path=tmp_path/'fresh.db'
    database.init_db(path,seed=False)
    with sqlite3.connect(path) as con:
        assert 'final_billing_month' in _columns(con,'students')

def test_existing_db_without_column_gets_migrated(tmp_path):
    path=tmp_path/'legacy.db'
    # あえて final_billing_month の無い旧スキーマでテーブルを作る（既存DBを模擬）
    with sqlite3.connect(path) as con:
        con.execute("""CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            school_location TEXT NOT NULL DEFAULT '', grade TEXT NOT NULL DEFAULT '',
            monthly_fee INTEGER NOT NULL DEFAULT 0, recital_fee INTEGER NOT NULL DEFAULT 0,
            enrollment_date TEXT, withdrawal_date TEXT, enrollment_status TEXT NOT NULL DEFAULT '在籍',
            guardian_name TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT '', notes TEXT DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        con.execute("INSERT INTO students(name,created_at,updated_at) VALUES('既存生徒','2026-01-01','2026-01-01')")
    with sqlite3.connect(path) as con:
        assert 'final_billing_month' not in _columns(con,'students')
    # 既存DBに対してinit_dbを実行すると、データを消さずに列だけ追加される
    database.init_db(path,seed=False)
    with sqlite3.connect(path) as con:
        assert 'final_billing_month' in _columns(con,'students')
        row=con.execute("SELECT name,final_billing_month FROM students WHERE name='既存生徒'").fetchone()
        assert row==('既存生徒',None)

def test_migration_is_idempotent_when_run_twice(tmp_path):
    path=tmp_path/'twice.db'
    database.init_db(path,seed=False)
    database.init_db(path,seed=False)  # 2回目もエラーにならない
    with sqlite3.connect(path) as con:
        assert 'final_billing_month' in _columns(con,'students')

def test_final_billing_month_save_and_load_roundtrip(isolated_db):
    from services.student_service import save_student,list_students
    sid=save_student(dict(name='退会太郎',school_location='中央教室',grade='小学1年',monthly_fee=9000,recital_fee=15000,
      enrollment_date='2026-01-01',withdrawal_date='2026-07-20',enrollment_status='退会',
      final_billing_month='2026-07',guardian_name='',phone='',email='',notes=''),'試験')
    saved=[s for s in list_students() if s['student_id']==sid][0]
    assert saved['final_billing_month']=='2026-07'
    assert saved['withdrawal_date']=='2026-07-20'
