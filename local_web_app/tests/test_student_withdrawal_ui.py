from datetime import date
from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.common import now

ROOT=Path(__file__).resolve().parents[1]

def _freeze_today(monkeypatch,fixed_date):
    import app_pages.management as management
    class _FixedDate(date):
        @classmethod
        def today(cls): return fixed_date
    monkeypatch.setattr(management,'date',_FixedDate)

def _open_students(app):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if '生徒管理' in o][0]
    radios[0].set_value(option).run()

def _status_widget(app,sid):
    return [w for w in app.selectbox if w.key==f'status_{sid}'][0]

def _wd_widgets(app,sid):
    return [w for w in app.date_input if w.key==f'wd_{sid}']

def _fbm_widgets(app,sid):
    return [w for w in app.selectbox if w.key==f'fbm_{sid}']

def _submit(app,sid):
    return [w for w in app.button if w.key==f'FormSubmitter:edit{sid}-変更を保存'][0]

def _first_active_student_id(isolated_db):
    import database
    with database.connect() as con:
        cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
          withdrawal_date,enrollment_status,final_billing_month,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          ('在籍花子','中央教室','小学1年',9000,15000,'2026-01-01',None,'在籍',None,now(),now()))
        return cur.lastrowid

def test_withdrawal_fields_hidden_for_active_student(isolated_db):
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    assert not _wd_widgets(app,sid)
    assert not _fbm_widgets(app,sid)

def test_selecting_withdrawn_reveals_fields_with_defaults(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('退会').run()
    assert not app.exception,app.exception
    wd=_wd_widgets(app,sid); fbm=_fbm_widgets(app,sid)
    assert wd and wd[0].value==date(2026,7,23)
    assert fbm and fbm[0].value=='2026-07'

def test_status_on_hold_does_not_reveal_fields(isolated_db):
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('休会').run()
    assert not _wd_widgets(app,sid)
    assert not _fbm_widgets(app,sid)

def test_changing_withdrawal_date_updates_final_billing_month_when_not_manually_set(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('退会').run()
    _wd_widgets(app,sid)[0].set_value(date(2026,9,10)).run()
    assert _fbm_widgets(app,sid)[0].value=='2026-09'

def test_manual_final_billing_month_is_not_overwritten_by_later_withdrawal_date_change(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('退会').run()
    # 先生が最終請求月を手動で6月に変更する
    _fbm_widgets(app,sid)[0].set_value('2026-06').run()
    assert _fbm_widgets(app,sid)[0].value=='2026-06'
    # その後、退会日を9月へ変更しても、手動変更した最終請求月は上書きされない
    _wd_widgets(app,sid)[0].set_value(date(2026,9,10)).run()
    assert _fbm_widgets(app,sid)[0].value=='2026-06'

def test_save_blocked_when_withdrawal_fields_incomplete(isolated_db):
    import database
    with database.connect() as con:
        cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
          withdrawal_date,enrollment_status,final_billing_month,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          ('未設定退会者','中央教室','小学1年',9000,15000,'2026-01-01',None,'退会',None,now(),now()))
        sid=cur.lastrowid
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    # 既に退会だが退会日・最終請求月とも未設定 → 空欄のまま
    assert _wd_widgets(app,sid)[0].value is None
    assert _fbm_widgets(app,sid)[0].value is None
    _submit(app,sid).click().run()
    assert not app.exception,app.exception
    errors=[w.value for w in app.error]
    assert any('退会日とレッスン料の最終請求月' in e for e in errors)
    saved=[s for s in database.query("SELECT * FROM students WHERE student_id=?",(sid,))][0]
    assert saved['enrollment_status']=='退会' and saved['final_billing_month'] is None

def test_save_succeeds_when_withdrawal_fields_complete(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    sid=_first_active_student_id(isolated_db)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('退会').run()
    _submit(app,sid).click().run()
    assert not app.exception,app.exception
    successes=[w.value for w in app.success]
    assert any('保存しました' in s for s in successes)
    import database
    saved=[s for s in database.query("SELECT * FROM students WHERE student_id=?",(sid,))][0]
    assert saved['enrollment_status']=='退会'
    assert saved['withdrawal_date']=='2026-07-23'
    assert saved['final_billing_month']=='2026-07'

def test_reverting_to_active_preserves_existing_withdrawal_history(isolated_db):
    import database
    with database.connect() as con:
        cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
          withdrawal_date,enrollment_status,final_billing_month,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          ('復帰太郎','中央教室','小学1年',9000,15000,'2025-01-01','2026-05-31','退会','2026-05',now(),now()))
        sid=cur.lastrowid
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_students(app)
    _status_widget(app,sid).set_value('在籍').run()
    assert not _wd_widgets(app,sid)  # 在籍に戻すと入力欄は表示されない
    _submit(app,sid).click().run()
    assert not app.exception,app.exception
    saved=[s for s in database.query("SELECT * FROM students WHERE student_id=?",(sid,))][0]
    assert saved['enrollment_status']=='在籍'
    # 履歴として保持され、削除されない
    assert saved['withdrawal_date']=='2026-05-31'
    assert saved['final_billing_month']=='2026-05'
