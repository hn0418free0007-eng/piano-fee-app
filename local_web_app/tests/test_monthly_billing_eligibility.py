from services import charge_service
from services.common import now

def _add_student(con,name='テスト生徒',status='在籍',enrollment_date=None,withdrawal_date=None,final_billing_month=None,monthly_fee=9000):
    cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
      withdrawal_date,enrollment_status,final_billing_month,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (name,'中央教室','小学1年',monthly_fee,15000,enrollment_date,withdrawal_date,status,final_billing_month,now(),now()))
    return cur.lastrowid

def _add_charge(con,student_id,target_month,charge_type='月謝',status='請求中',amount=9000):
    con.execute("""INSERT INTO charges(student_id,target_month,charge_type,charge_amount,due_date,charge_status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?)""",(student_id,target_month,charge_type,amount,None,status,now(),now()))

def test_active_student_is_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='在籍',enrollment_date='2026-01-01')
    result=charge_service.monthly_billing_eligibility('2026-08')
    assert result[0]['eligible'] is True

def test_on_hold_student_is_not_eligible_with_reason(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='休会',enrollment_date='2026-01-01')
    result=charge_service.monthly_billing_eligibility('2026-08')
    assert result[0]['eligible'] is False
    assert result[0]['reason']=='休会のため対象外'

def test_withdrawn_student_same_month_as_final_billing_is_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='退会',enrollment_date='2026-01-01',withdrawal_date='2026-07-20',final_billing_month='2026-07')
    result=charge_service.monthly_billing_eligibility('2026-07')
    assert result[0]['eligible'] is True

def test_withdrawn_student_before_final_billing_month_is_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='退会',enrollment_date='2026-01-01',final_billing_month='2026-07')
    result=charge_service.monthly_billing_eligibility('2026-06')
    assert result[0]['eligible'] is True

def test_withdrawn_student_after_final_billing_month_is_not_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='退会',enrollment_date='2026-01-01',final_billing_month='2026-07')
    result=charge_service.monthly_billing_eligibility('2026-08')
    assert result[0]['eligible'] is False
    assert '最終請求月' in result[0]['reason']

def test_withdrawn_student_without_final_billing_month_is_not_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='退会',enrollment_date='2026-01-01',final_billing_month=None)
    result=charge_service.monthly_billing_eligibility('2026-07')
    assert result[0]['eligible'] is False
    assert '要確認' in result[0]['reason']

def test_enrollment_month_is_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='在籍',enrollment_date='2026-08-15')
    result=charge_service.monthly_billing_eligibility('2026-08')
    assert result[0]['eligible'] is True

def test_before_enrollment_month_is_not_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='在籍',enrollment_date='2026-08-15')
    result=charge_service.monthly_billing_eligibility('2026-07')
    assert result[0]['eligible'] is False
    assert result[0]['reason']=='入会月より前のため対象外'

def test_missing_enrollment_date_is_compatible_and_eligible(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='在籍',enrollment_date=None)
    result=charge_service.monthly_billing_eligibility('2026-01')
    assert result[0]['eligible'] is True

def test_already_billed_month_is_marked_already_billed(isolated_db):
    import database
    with database.connect() as con:
        sid=_add_student(con,status='在籍',enrollment_date='2026-01-01')
        _add_charge(con,sid,'2026-08')
    result=charge_service.monthly_billing_eligibility('2026-08')
    assert result[0]['eligible'] is True
    assert result[0]['already_billed'] is True

def test_create_monthly_skips_already_billed_and_ineligible(isolated_db):
    import database
    with database.connect() as con:
        active=_add_student(con,name='在籍太郎',status='在籍',enrollment_date='2026-01-01',monthly_fee=9000)
        on_hold=_add_student(con,name='休会花子',status='休会',enrollment_date='2026-01-01',monthly_fee=9000)
        withdrawn_ok=_add_student(con,name='退会次郎',status='退会',enrollment_date='2026-01-01',final_billing_month='2026-08',monthly_fee=9000)
        withdrawn_unset=_add_student(con,name='退会三郎',status='退会',enrollment_date='2026-01-01',final_billing_month=None,monthly_fee=9000)
    r=charge_service.create_monthly('2026-08','2026-07-31','試験')
    assert r['created']==2  # 在籍太郎・退会次郎のみ
    charged_ids={row['student_id'] for row in database.query("SELECT student_id FROM charges WHERE target_month='2026-08' AND charge_type='月謝'")}
    assert charged_ids=={active,withdrawn_ok}
    assert on_hold not in charged_ids
    assert withdrawn_unset not in charged_ids

def test_create_monthly_with_student_ids_filters_selection(isolated_db):
    import database
    with database.connect() as con:
        s1=_add_student(con,name='生徒1',status='在籍',enrollment_date='2026-01-01',monthly_fee=9000)
        s2=_add_student(con,name='生徒2',status='在籍',enrollment_date='2026-01-01',monthly_fee=11000)
    r=charge_service.create_monthly('2026-08','2026-07-31','試験',student_ids=[s1])
    assert r['created']==1 and r['total']==9000
    charged_ids={row['student_id'] for row in database.query("SELECT student_id FROM charges WHERE target_month='2026-08'")}
    assert charged_ids=={s1}

def test_create_monthly_duplicate_run_is_skipped(isolated_db):
    import database
    with database.connect() as con:
        _add_student(con,status='在籍',enrollment_date='2026-01-01')
    r1=charge_service.create_monthly('2026-08','2026-07-31','試験')
    assert r1['created']==1
    r2=charge_service.create_monthly('2026-08','2026-07-31','試験')
    assert r2['created']==0 and r2['skipped']==1

def test_invalid_target_month_format_raises():
    import pytest
    with pytest.raises(ValueError):
        charge_service.monthly_billing_eligibility('2026-8')
