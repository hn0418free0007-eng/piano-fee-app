from collections import defaultdict
from database import query
from services.auth_service import get_client,current_user,is_cloud_configured
from services.common import today_jst

def _cloud(): return is_cloud_configured() and bool(current_user())
def _payments():
    if _cloud(): return get_client().table('payments').select('student_id,student_name,target_month,payment_type,amount_received,received_date,cancelled_at').is_('cancelled_at','null').execute().data
    return query("SELECT student_id,student_name,target_month,payment_type,amount_received,received_date,cancelled_at FROM payments WHERE cancelled_at IS NULL")

def _payments_on(day):
    if _cloud(): return get_client().table('payments').select('amount_received').eq('received_date',day).is_('cancelled_at','null').execute().data
    return query("SELECT amount_received FROM payments WHERE received_date=? AND cancelled_at IS NULL",(day,))

# 受領日ベース: 指定日にreceived_dateを持つ、取消されていない入金の合計。該当が無ければ0。
def daily_received_amount(day=None):
    day=day or today_jst()
    return sum(p['amount_received'] for p in _payments_on(day))

def today_received_amount():
    return daily_received_amount()

# 請求月ベース: target_month（何月分の請求か）を基準に集計する。月謝管理・請求状況・未収管理向け。
def monthly_billed_amount(target_month):
    totals=defaultdict(int)
    for p in _payments():
        if p['target_month']==target_month: totals[(p['student_name'],p['payment_type'])]+=p['amount_received']
    return [{'生徒名':k[0],'請求種別':k[1],'金額':v} for k,v in sorted(totals.items())]

# 受領日ベース: received_date（実際に受け取った日）を基準に集計する。入金実績・現金管理向け。
def monthly_received_amount(received_month):
    totals=defaultdict(int)
    for p in _payments():
        if str(p['received_date'])[:7]==received_month: totals[(p['student_name'],p['payment_type'])]+=p['amount_received']
    return [{'生徒名':k[0],'請求種別':k[1],'金額':v} for k,v in sorted(totals.items())]

def yearly_billed_amount(year):
    totals=defaultdict(int)
    for p in _payments():
        tm=str(p['target_month'])
        if tm[:4]==str(year): totals[int(tm[5:7])]+=p['amount_received']
    return [{'月':m,'金額':totals[m]} for m in range(1,13)]

def yearly_received_amount(year):
    totals=defaultdict(int)
    for p in _payments():
        d=str(p['received_date'])
        if d[:4]==str(year): totals[int(d[5:7])]+=p['amount_received']
    return [{'月':m,'金額':totals[m]} for m in range(1,13)]

def student_yearly_billed_amount(year):
    totals=defaultdict(int)
    for p in _payments():
        tm=str(p['target_month'])
        if tm[:4]==str(year): totals[(p['student_name'],int(tm[5:7]))]+=p['amount_received']
    return [{'生徒名':k[0],'月':k[1],'金額':v} for k,v in sorted(totals.items())]

def student_yearly_received_amount(year):
    totals=defaultdict(int)
    for p in _payments():
        d=str(p['received_date'])
        if d[:4]==str(year): totals[(p['student_name'],int(d[5:7]))]+=p['amount_received']
    return [{'生徒名':k[0],'月':k[1],'金額':v} for k,v in sorted(totals.items())]

# 発表会費は開催（＝target_month）に紐づく請求であり、受領日ベースの区別は行わない。
def recital_billed_amount(year_or_event=''):
    totals=defaultdict(int)
    for p in _payments():
        if p['payment_type']=='発表会費' and (not year_or_event or year_or_event in p['target_month']): totals[(p['target_month'],p['student_name'])]+=p['amount_received']
    return [{'開催名':k[0],'生徒名':k[1],'金額':v} for k,v in sorted(totals.items())]
