from collections import defaultdict
from database import query
from services.auth_service import get_client,current_user,is_cloud_configured

def _cloud(): return is_cloud_configured() and bool(current_user())
def _payments():
    if _cloud(): return get_client().table('payments').select('student_id,student_name,target_month,payment_type,amount_received,received_date,cancelled_at').is_('cancelled_at','null').execute().data
    return query("SELECT student_id,student_name,target_month,payment_type,amount_received,received_date,cancelled_at FROM payments WHERE cancelled_at IS NULL")

def monthly_sales(year_month):
    totals=defaultdict(int)
    for p in _payments():
        if str(p['received_date'])[:7]==year_month: totals[(p['student_name'],p['payment_type'])]+=p['amount_received']
    return [{'生徒名':k[0],'請求種別':k[1],'売上金額':v} for k,v in sorted(totals.items())]

def yearly_sales(year):
    totals=defaultdict(int)
    for p in _payments():
        d=str(p['received_date'])
        if d[:4]==str(year): totals[int(d[5:7])]+=p['amount_received']
    return [{'月':m,'売上金額':totals[m]} for m in range(1,13)]

def student_yearly_sales(year):
    totals=defaultdict(int)
    for p in _payments():
        d=str(p['received_date'])
        if d[:4]==str(year): totals[(p['student_name'],int(d[5:7]))]+=p['amount_received']
    return [{'生徒名':k[0],'月':k[1],'売上金額':v} for k,v in sorted(totals.items())]

def recital_sales(year_or_event=''):
    totals=defaultdict(int)
    for p in _payments():
        if p['payment_type']=='発表会費' and (not year_or_event or year_or_event in p['target_month']): totals[(p['target_month'],p['student_name'])]+=p['amount_received']
    return [{'開催名':k[0],'生徒名':k[1],'売上金額':v} for k,v in sorted(totals.items())]
