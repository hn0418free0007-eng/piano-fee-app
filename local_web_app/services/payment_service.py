from database import connect, now
from services.common import audit

def _cloud_client():
    from services.auth_service import is_cloud_configured,current_user,get_client
    return get_client() if is_cloud_configured() and current_user() else None

def register_payment(charge_id,amount,received_date,method,operator,notes="",allow_extra=False):
    amount=int(amount)
    cloud=_cloud_client()
    if cloud:
        c=cloud.table('charges').select('*,students(name)').eq('charge_id',charge_id).single().execute().data
        pays=cloud.table('payments').select('amount_received').eq('charge_id',charge_id).is_('cancelled_at','null').execute().data
        paid=sum(p['amount_received'] for p in pays); remaining=c['charge_amount']-paid
        if remaining<=0 and not allow_extra: raise ValueError(f"{c['target_month']}の{c['charge_type']}は、すでに受領登録されています。")
        if amount<=0: raise ValueError('受取額は1円以上にしてください。')
        if amount>remaining and not allow_extra: raise ValueError('残額を超えています。追加徴収として確認してください。')
        status='一部入金' if amount<remaining else '受領済・印鑑未確認'; student_name=c.get('students',{}).get('name','')
        row=cloud.table('payments').insert({'charge_id':charge_id,'student_id':c['student_id'],'student_name':student_name,'target_month':c['target_month'],'payment_type':c['charge_type'],'charge_amount':c['charge_amount'],'amount_received':amount,'received_date':received_date,'received_time':__import__('datetime').datetime.now().strftime('%H:%M:%S'),'payment_method':method,'received_by':operator,'stamp_confirmed':False,'payment_status':status,'notes':notes}).execute().data[0]
        cloud.table('charges').update({'charge_status':'入金済' if paid+amount>=c['charge_amount'] else '一部入金','updated_at':now()}).eq('charge_id',charge_id).execute()
        cloud.table('audit_logs').insert({'action_type':'受領登録','target_table':'payments','target_id':row['payment_id'],'student_id':c['student_id'],'action_detail':f"{c['target_month']} {c['charge_type']} {amount}円",'operator_name':operator}).execute(); return row['payment_id']
    with connect() as con:
        c=con.execute("SELECT c.*,s.name FROM charges c JOIN students s USING(student_id) WHERE charge_id=?",(charge_id,)).fetchone()
        if not c: raise ValueError("請求が見つかりません。")
        paid=con.execute("SELECT COALESCE(SUM(amount_received),0) FROM payments WHERE charge_id=? AND cancelled_at IS NULL",(charge_id,)).fetchone()[0]
        remaining=c['charge_amount']-paid
        if remaining<=0 and not allow_extra: raise ValueError(f"{c['target_month']}の{c['charge_type']}は、すでに受領登録されています。")
        if amount<=0: raise ValueError("受取額は1円以上にしてください。")
        if amount>remaining and not allow_extra: raise ValueError("残額を超えています。追加徴収として確認してください。")
        stamp=now(); status='一部入金' if amount<remaining else '受領済・印鑑未確認'
        cur=con.execute("""INSERT INTO payments(charge_id,student_id,student_name,target_month,payment_type,charge_amount,amount_received,
          received_date,received_time,payment_method,received_by,stamp_confirmed,payment_status,notes,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,time('now','localtime'),?,?,0,?,?,?,?)""",(charge_id,c['student_id'],c['name'],c['target_month'],c['charge_type'],c['charge_amount'],amount,received_date,method,operator,status,notes,stamp,stamp))
        newpaid=paid+amount; cs='入金済' if newpaid>=c['charge_amount'] else '一部入金'
        con.execute("UPDATE charges SET charge_status=?,updated_at=? WHERE charge_id=?",(cs,stamp,charge_id))
        audit(con,"受領登録","payments",cur.lastrowid,c['student_id'],f"{c['target_month']} {c['charge_type']} {amount}円",operator)
        return cur.lastrowid

def pending_stamps():
    cloud=_cloud_client()
    if cloud: return cloud.table('payments').select('*').eq('stamp_confirmed',False).is_('cancelled_at','null').order('received_date').order('received_time').execute().data
    return [dict(r) for r in connect().execute("""SELECT * FROM payments WHERE stamp_confirmed=0 AND cancelled_at IS NULL ORDER BY received_date,received_time""").fetchall()]

def confirm_stamp(payment_id,operator):
    cloud=_cloud_client()
    if cloud:
        rows=cloud.table('payments').select('*').eq('payment_id',payment_id).is_('cancelled_at','null').execute().data
        if not rows: raise ValueError('有効な入金が見つかりません。')
        p=rows[0]; stamp=now(); cloud.table('payments').update({'stamp_confirmed':True,'stamp_confirmed_at':stamp,'stamp_confirmed_by':operator,'payment_status':'処理完了','updated_at':stamp}).eq('payment_id',payment_id).execute()
        cloud.table('audit_logs').insert({'action_type':'印鑑確認','target_table':'payments','target_id':payment_id,'student_id':p['student_id'],'action_detail':'封筒の受領印を確認','operator_name':operator}).execute(); return
    with connect() as con:
        p=con.execute("SELECT * FROM payments WHERE payment_id=? AND cancelled_at IS NULL",(payment_id,)).fetchone()
        if not p: raise ValueError("有効な入金が見つかりません。")
        stamp=now(); con.execute("UPDATE payments SET stamp_confirmed=1,stamp_confirmed_at=?,stamp_confirmed_by=?,payment_status='処理完了',updated_at=? WHERE payment_id=?",(stamp,operator,stamp,payment_id))
        audit(con,"印鑑確認","payments",payment_id,p['student_id'],"封筒の受領印を確認",operator)

def cancel_payment(payment_id,reason,operator):
    if not reason.strip(): raise ValueError("取消理由を入力してください。")
    cloud=_cloud_client()
    if cloud:
        rows=cloud.table('payments').select('*').eq('payment_id',payment_id).is_('cancelled_at','null').execute().data
        if not rows: raise ValueError('有効な入金が見つかりません。')
        p=rows[0]; stamp=now(); cloud.table('payments').update({'payment_status':'取消','cancelled_at':stamp,'cancellation_reason':reason,'updated_at':stamp}).eq('payment_id',payment_id).execute()
        valid=cloud.table('payments').select('amount_received').eq('charge_id',p['charge_id']).is_('cancelled_at','null').execute().data; paid=sum(x['amount_received'] for x in valid)
        cs='請求中' if paid==0 else ('一部入金' if paid<p['charge_amount'] else '入金済'); cloud.table('charges').update({'charge_status':cs,'updated_at':stamp}).eq('charge_id',p['charge_id']).execute()
        cloud.table('audit_logs').insert({'action_type':'入金取消','target_table':'payments','target_id':payment_id,'student_id':p['student_id'],'action_detail':reason,'operator_name':operator}).execute(); return
    with connect() as con:
        p=con.execute("SELECT * FROM payments WHERE payment_id=? AND cancelled_at IS NULL",(payment_id,)).fetchone()
        if not p: raise ValueError("有効な入金が見つかりません。")
        stamp=now(); con.execute("UPDATE payments SET payment_status='取消',cancelled_at=?,cancellation_reason=?,updated_at=? WHERE payment_id=?",(stamp,reason,stamp,payment_id))
        paid=con.execute("SELECT COALESCE(SUM(amount_received),0) FROM payments WHERE charge_id=? AND cancelled_at IS NULL",(p['charge_id'],)).fetchone()[0]
        cs='請求中' if paid==0 else ('一部入金' if paid<p['charge_amount'] else '入金済')
        con.execute("UPDATE charges SET charge_status=?,updated_at=? WHERE charge_id=?",(cs,stamp,p['charge_id']))
        audit(con,"入金取消","payments",payment_id,p['student_id'],reason,operator)

def history(filters=None):
    filters=filters or {}; sql="SELECT * FROM payments WHERE 1=1"; p=[]
    cloud=_cloud_client()
    if cloud:
        q=cloud.table('payments').select('*')
        for key,col in [('name','student_name'),('target_month','target_month'),('received_date','received_date'),('method','payment_method'),('operator','received_by'),('charge_type','payment_type')]:
            if filters.get(key): q=q.ilike(col,f"%{filters[key]}%")
        return q.order('received_date',desc=True).order('received_time',desc=True).execute().data
    for key,col in [('name','student_name'),('target_month','target_month'),('received_date','received_date'),('method','payment_method'),('operator','received_by'),('charge_type','payment_type')]:
        if filters.get(key): sql+=f" AND {col} LIKE ?"; p.append(f"%{filters[key]}%")
    return [dict(r) for r in connect().execute(sql+" ORDER BY received_date DESC,received_time DESC",p).fetchall()]
