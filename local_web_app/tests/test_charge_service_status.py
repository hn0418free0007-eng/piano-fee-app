import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from services import charge_service
from services.common import now

def _add_student(con):
    cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?)""",('テスト生徒','中央教室','小学1年',9000,15000,'在籍',now(),now()))
    return cur.lastrowid

def _add_charge(con,student_id,target_month,due_date,charge_status,charge_type='月謝',amount=9000):
    con.execute("""INSERT INTO charges(student_id,target_month,charge_type,charge_amount,due_date,charge_status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?)""",(student_id,target_month,charge_type,amount,due_date,charge_status,now(),now()))

def test_paid_through_reference_month(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','入金済')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status=={'state':'paid','target_month':'2026-08','due_date':None,'overdue_days':None}

def test_unpaid_due_soon(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status=={'state':'due_soon','target_month':'2026-08','due_date':'2026-07-31','overdue_days':None}

def test_unpaid_due_today(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-31')
    assert status=={'state':'due_today','target_month':'2026-08','due_date':'2026-07-31','overdue_days':0}

def test_unpaid_overdue_days_correct(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-08-01')
    assert status['state']=='overdue'
    assert status['target_month']=='2026-08'
    assert status['due_date']=='2026-07-31'
    assert status['overdue_days']==1

def test_missing_charge_after_paid_month(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        # 7月分は支払済みだが、8月分の請求がまだ作成されていない
        _add_charge(con,sid,'2026-07','2026-06-30','入金済')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status=={'state':'missing','target_month':'2026-08','due_date':None,'overdue_days':None}

def test_missing_charge_with_no_history(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['state']=='missing'
    assert status['target_month']=='2026-08'

def test_recital_fee_does_not_affect_monthly_status(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','入金済')
        _add_charge(con,sid,'2026年度発表会','2026-09-01','請求中',charge_type='発表会費',amount=15000)
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['state']=='paid'
    assert status['target_month']=='2026-08'

def test_multiple_unpaid_months_picks_oldest_due_date(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','請求中')
        _add_charge(con,sid,'2026-07','2026-06-30','請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['target_month']=='2026-07'
    assert status['due_date']=='2026-06-30'
    assert status['state']=='overdue'
    assert status['overdue_days']==23

def test_cancelled_charge_ignored(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08','2026-07-31','取消')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['state']=='missing'
    assert status['target_month']=='2026-08'

def test_unpaid_without_due_date_is_due_unset_not_due_soon(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-08',None,'請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status=={'state':'due_unset','target_month':'2026-08','due_date':None,'overdue_days':None}

def test_due_unset_takes_lowest_target_month_when_multiple(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-09',None,'請求中')
        _add_charge(con,sid,'2026-08',None,'請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['state']=='due_unset'
    assert status['target_month']=='2026-08'

def test_due_dated_unpaid_takes_priority_over_due_unset(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2026-09',None,'請求中')
        _add_charge(con,sid,'2026-08','2026-07-31','請求中')
    status=charge_service.monthly_payment_status(sid,today='2026-07-23')
    assert status['state']=='due_soon'
    assert status['target_month']=='2026-08'

def test_unpaid_due_state_label(isolated_db):
    today='2026-07-23'
    assert charge_service._due_state_label('2026-08-31',today)=='期限前'
    assert charge_service._due_state_label('2026-07-23',today)=='本日期限'
    assert charge_service._due_state_label('2026-07-01',today)=='期限超過'
    assert charge_service._due_state_label(None,today)=='期限未設定'

def test_unpaid_list_includes_status_column(isolated_db):
    import database
    from services.common import today_jst
    today=today_jst()
    with database.connect() as con:
        sid=_add_student(con)
        _add_charge(con,sid,'2099-01','2099-01-31','請求中')
        _add_charge(con,sid,'2099-02',None,'請求中')
    rows={r['target_month']:r for r in charge_service.unpaid()}
    assert rows['2099-01']['状態']=='期限前'
    assert rows['2099-02']['状態']=='期限未設定'
    assert today  # 参考: today_jstが利用可能であることの確認
