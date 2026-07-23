from datetime import date
from types import SimpleNamespace
from services.calendar_service import fetch_today_events,match_students,normalize_title
from services.calendar_mapping_service import save_mapping,get_mappings
from services.student_service import save_student
from services.charge_service import create_monthly,open_charges
from services.payment_service import history
import services.v3_repository as v3_repository
from services.v3_repository import complete
from services.common import today_jst
from services.sales_service import monthly_received_amount,yearly_received_amount,student_yearly_received_amount
from services.export_service import to_csv,to_excel

def test_calendar_to_sales_export(isolated_db,monkeypatch):
    s=dict(name='カレンダー生徒',school_location='中央教室',grade='小学3年',monthly_fee=12000,recital_fee=15000,
      enrollment_date='2026-04-01',withdrawal_date=None,enrollment_status='在籍',guardian_name='',phone='',email='',notes='')
    today=today_jst(); sid=save_student(s,'試験'); create_monthly(today[:7],today,'試験')
    events=fetch_today_events(None,day=date.today()); events[0]['title']='カレンダー生徒'
    matched=match_students(events,[dict(s,student_id=sid)])
    assert matched[0]['match_status']=='自動照合' and matched[-1]['match_status']=='未照合'
    monkeypatch.setattr('services.v3_repository.cloud_active',lambda:False)
    charge=open_charges(sid)[0]; complete(charge,dict(s,student_id=sid),'現金','先生',events[0]['event_id'])
    assert history({'name':'カレンダー生徒'})[0]['payment_status']=='処理完了'
    rows=monthly_received_amount(today[:7]); assert rows[0]['金額']==12000
    assert sum(r['金額'] for r in yearly_received_amount(int(today[:4])))>=12000
    assert student_yearly_received_amount(int(today[:4]))[0]['生徒名']=='カレンダー生徒'
    assert to_csv(rows).startswith(b'\xef\xbb\xbf') and to_excel(rows).startswith(b'PK')
    # 全角空白・連続空白・安全な接尾語を正規化する。
    assert normalize_title('  カレンダー生徒　 レッスン  ')=='カレンダー生徒'
    # 未照合を手動保存し、次回照合へ利用する。
    save_mapping(normalize_title('別名 レッスン'),'別名 レッスン',sid,'先生')
    mapped=match_students([dict(events[0],title='別名 レッスン')],[dict(s,student_id=sid)],get_mappings())
    assert mapped[0]['student']['student_id']==sid and mapped[0]['match_status']=='手動照合'
    # 全額完了後は同じ請求を再登録できない。
    import pytest
    with pytest.raises(ValueError): complete(charge,dict(s,student_id=sid),'現金','先生',events[0]['event_id'])


class _FakeRpc:
    def __init__(self, name, params, result): self.name=name; self.params=params; self._result=result
    def execute(self): return SimpleNamespace(data=self._result)

class _FakeCloudClient:
    def __init__(self, result): self.result=result; self.calls=[]
    def rpc(self, name, params):
        call=_FakeRpc(name, params, self.result); self.calls.append(call); return call

def test_complete_cloud_branch_passes_jst_received_date_to_rpc(monkeypatch):
    """
    v3_repository.complete()のクラウド分岐が、complete_lesson_payment RPCへ
    p_received_dateとしてtoday_jst()の値を明示的に渡すことを検証する
    （RPC側のcurrent_dateフォールバックに任せきりにしない）。
    """
    fake_client=_FakeCloudClient(result=999)
    monkeypatch.setattr(v3_repository, 'cloud_active', lambda: True)
    monkeypatch.setattr(v3_repository, 'get_client', lambda: fake_client)

    charge=dict(charge_id=1, charge_amount=9000, paid=0)
    pid=complete(charge, dict(student_id=1), '現金', '先生', 'event-1')

    assert pid == 999
    assert len(fake_client.calls) == 1
    call=fake_client.calls[0]
    assert call.name == 'complete_lesson_payment'
    assert call.params['p_received_date'] == today_jst()
    assert call.params['p_charge_id'] == 1
    assert call.params['p_calendar_event_id'] == 'event-1'
