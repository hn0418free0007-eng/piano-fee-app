from datetime import date
import pytest
from services.student_service import save_student,list_students
from services.charge_service import create_monthly,open_charges,unpaid
from services.payment_service import register_payment,confirm_stamp,pending_stamps,history,cancel_payment
from services.export_service import to_csv,to_excel

def student(name='テスト生徒'):
    return dict(name=name,school_location='試験教室',grade='小1',monthly_fee=10000,recital_fee=15000,enrollment_date='2026-04-01',withdrawal_date=None,enrollment_status='在籍',guardian_name='',phone='',email='',notes='')

def test_full_workflow(isolated_db):
    sid=save_student(student(),'試験'); assert list_students(status='在籍')[0]['student_id']==sid
    r=create_monthly('2026-08','2026-08-10','試験'); assert r['created']==1 and r['total']==10000
    r=create_monthly('2026-08','2026-08-10','試験'); assert r['created']==0 and r['skipped']==1
    charge=open_charges(sid)[0]
    pid=register_payment(charge['charge_id'],4000,date.today().isoformat(),'現金','試験'); assert unpaid({'state':'一部入金'})[0]['unpaid']==6000
    assert pending_stamps()[0]['payment_id']==pid
    confirm_stamp(pid,'試験'); assert not pending_stamps()
    register_payment(charge['charge_id'],6000,date.today().isoformat(),'現金','試験')
    with pytest.raises(ValueError): register_payment(charge['charge_id'],100,date.today().isoformat(),'現金','試験')
    rows=history({'name':'テスト'}); assert len(rows)==2
    cancel_payment(rows[0]['payment_id'],'入力試験','試験'); assert history()[0]['payment_status']=='取消'

def test_exports(isolated_db):
    rows=[{'氏名':'架空生徒','金額':1000}]
    assert to_csv(rows).startswith(b'\xef\xbb\xbf')
    assert to_excel(rows).startswith(b'PK')

