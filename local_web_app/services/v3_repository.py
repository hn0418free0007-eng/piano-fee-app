from __future__ import annotations
from datetime import date,datetime
from database import connect,now
from services.auth_service import get_client,is_cloud_configured,current_user
from services.student_service import list_students
from services.charge_service import open_charges
from services.payment_service import register_payment,confirm_stamp

def cloud_active(): return is_cloud_configured() and bool(current_user())

def students():
    if cloud_active(): return get_client().table('students').select('*').eq('enrollment_status','在籍').order('name').execute().data
    return list_students(status='在籍')

def charges(student_id):
    if not cloud_active(): return open_charges(student_id)
    c=get_client(); rows=c.table('charges').select('*').eq('student_id',student_id).in_('charge_status',['請求中','一部入金']).execute().data
    pays=c.table('payments').select('charge_id,amount_received,cancelled_at').eq('student_id',student_id).execute().data
    for row in rows: row['paid']=sum(p['amount_received'] for p in pays if p['charge_id']==row['charge_id'] and not p['cancelled_at'])
    return [r for r in rows if r['paid']<r['charge_amount']]

def complete(charge,student,method,operator,event_id=None):
    amount=int(charge['charge_amount']-charge.get('paid',0))
    if cloud_active():
        result=get_client().rpc('complete_lesson_payment',{'p_charge_id':charge['charge_id'],'p_payment_method':method,
          'p_received_by':operator,'p_calendar_event_id':event_id}).execute()
        return int(result.data)
    pid=register_payment(charge['charge_id'],amount,date.today().isoformat(),method,operator,f'Google Calendar: {event_id or "なし"}')
    confirm_stamp(pid,operator); return pid
