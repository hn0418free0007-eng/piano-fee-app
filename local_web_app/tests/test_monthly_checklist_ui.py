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

def _open_monthly(app):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if '月次請求' in o][0]
    radios[0].set_value(option).run()

def _select_target_month(app,label):
    sb=[w for w in app.selectbox if w.label=='レッスン料の対象月'][0]
    sb.select(label).run()

def _seed(con,name,status='在籍',enrollment_date='2026-01-01',final_billing_month=None,monthly_fee=9000):
    cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
      withdrawal_date,enrollment_status,final_billing_month,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (name,'中央教室','小学1年',monthly_fee,15000,enrollment_date,None,status,final_billing_month,now(),now()))
    return cur.lastrowid

def test_eligible_students_checked_by_default_ineligible_have_no_checkbox(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    with database.connect() as con:
        active=_seed(con,'在籍花子',status='在籍')
        on_hold=_seed(con,'休会太郎',status='休会')
        withdrawn_unset=_seed(con,'退会次郎',status='退会',final_billing_month=None)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    assert not app.exception,app.exception
    checkboxes={w.label:w for w in app.checkbox if w.label and w.label.startswith(('在籍花子','休会太郎','退会次郎'))}
    assert any(l.startswith('在籍花子') for l in checkboxes)
    assert not any(l.startswith('休会太郎') for l in checkboxes)
    assert not any(l.startswith('退会次郎') for l in checkboxes)
    active_cb=[w for l,w in checkboxes.items() if l.startswith('在籍花子')][0]
    assert active_cb.value is True

def test_warning_shown_for_unset_final_billing_month(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    with database.connect() as con:
        _seed(con,'要確認太郎',status='退会',final_billing_month=None)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    warnings_=[w.value for w in app.warning]
    assert any('最終請求月が未設定の退会者が1名' in w and '要確認太郎' in w for w in warnings_)

def test_no_warning_when_no_unset_withdrawn_students(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    with database.connect() as con:
        _seed(con,'在籍花子',status='在籍')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    warnings_=[w.value for w in app.warning]
    assert not any('最終請求月が未設定' in w for w in warnings_)

def test_unchecking_reduces_count_and_total(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    with database.connect() as con:
        s1=_seed(con,'生徒あ',monthly_fee=9000)
        s2=_seed(con,'生徒い',monthly_fee=11000)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    infos=[w.value for w in app.info]
    assert any('対象 2人' in i and '20,000円' in i for i in infos)
    cb=[w for w in app.checkbox if w.label and w.label.startswith('生徒い')][0]
    cb.set_value(False).run()
    infos=[w.value for w in app.info]
    assert any('対象 1人' in i and '9,000円' in i for i in infos)

def test_only_checked_eligible_unbilled_students_get_created(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    with database.connect() as con:
        s1=_seed(con,'生徒あ',monthly_fee=9000)
        s2=_seed(con,'生徒い',monthly_fee=11000)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    cb=[w for w in app.checkbox if w.label and w.label.startswith('生徒い')][0]
    cb.set_value(False).run()
    confirm=[w for w in app.checkbox if w.label=='対象人数と金額を確認しました'][0]
    confirm.set_value(True).run()
    create_btn=[w for w in app.button if '請求作成' in (w.label or '')][0]
    create_btn.click().run()
    assert not app.exception,app.exception
    charged={row['student_id'] for row in database.query("SELECT student_id FROM charges WHERE target_month='2026-08'")}
    assert charged=={s1}
    assert s2 not in charged

def test_already_created_charge_is_not_recreated(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    import database
    from services.charge_service import create_monthly
    with database.connect() as con:
        s1=_seed(con,'生徒あ',monthly_fee=9000)
    create_monthly('2026-08','2026-07-31','事前作成')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    _select_target_month(app,'2026年8月')
    # 既に作成済みなのでチェックボックス自体が出ない
    assert not [w for w in app.checkbox if w.label and w.label.startswith('生徒あ')]
    df=app.dataframe[0].value
    row=df[df['生徒名']=='生徒あ'].iloc[0]
    assert row['同月請求']=='作成済み'
