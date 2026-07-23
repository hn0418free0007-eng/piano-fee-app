from database import connect, now
from services.common import audit

def _cloud_client():
    from services.auth_service import is_cloud_configured,current_user,get_client
    return get_client() if is_cloud_configured() and current_user() else None

def create_monthly(target_month, due_date, operator):
    cloud=_cloud_client()
    if cloud:
        students=cloud.table('students').select('*').eq('enrollment_status','在籍').execute().data; created=skipped=total=0
        existing={r['student_id'] for r in cloud.table('charges').select('student_id').eq('target_month',target_month).eq('charge_type','月謝').execute().data}
        for s in students:
            if s['student_id'] in existing: skipped+=1; continue
            try:
                row=cloud.table('charges').insert({'student_id':s['student_id'],'target_month':target_month,'charge_type':'月謝','charge_amount':s['monthly_fee'],'due_date':due_date,'charge_status':'請求中'}).execute().data[0]
                cloud.table('audit_logs').insert({'action_type':'請求作成','target_table':'charges','target_id':row['charge_id'],'student_id':s['student_id'],'action_detail':f"{target_month} 月謝 {s['monthly_fee']}円",'operator_name':operator}).execute(); created+=1; total+=s['monthly_fee']
            except Exception: skipped+=1
        return {'created':created,'skipped':skipped,'total':total,'candidates':len(students)}
    created=skipped=total=0
    with connect() as con:
        students=con.execute("SELECT * FROM students WHERE enrollment_status='在籍'").fetchall()
        for s in students:
            try:
                cur=con.execute("""INSERT INTO charges(student_id,target_month,charge_type,charge_amount,due_date,charge_status,created_at,updated_at)
                    VALUES(?,?,'月謝',?,?,'請求中',?,?)""",(s['student_id'],target_month,s['monthly_fee'],due_date,now(),now()))
                audit(con,"請求作成","charges",cur.lastrowid,s['student_id'],f"{target_month} 月謝 {s['monthly_fee']}円",operator)
                created+=1; total+=s['monthly_fee']
            except Exception as e:
                if "UNIQUE" in str(e): skipped+=1
                else: raise
    return {"created":created,"skipped":skipped,"total":total,"candidates":len(students)}

def create_recital(student_ids,target,amounts,due_date,operator):
    cloud=_cloud_client()
    if cloud:
        created=skipped=total=0; existing={r['student_id'] for r in cloud.table('charges').select('student_id').eq('target_month',target).eq('charge_type','発表会費').execute().data}
        for sid in student_ids:
            if sid in existing: skipped+=1; continue
            amount=int(amounts[sid])
            try:
                row=cloud.table('charges').insert({'student_id':sid,'target_month':target,'charge_type':'発表会費','charge_amount':amount,'due_date':due_date,'charge_status':'請求中'}).execute().data[0]
                cloud.table('audit_logs').insert({'action_type':'請求作成','target_table':'charges','target_id':row['charge_id'],'student_id':sid,'action_detail':f'{target} 発表会費 {amount}円','operator_name':operator}).execute(); created+=1; total+=amount
            except Exception: skipped+=1
        return {'created':created,'skipped':skipped,'total':total}
    created=skipped=total=0
    with connect() as con:
        for sid in student_ids:
            amount=int(amounts[sid])
            try:
                cur=con.execute("INSERT INTO charges(student_id,target_month,charge_type,charge_amount,due_date,charge_status,created_at,updated_at) VALUES(?,?,'発表会費',?,?,'請求中',?,?)",(sid,target,amount,due_date,now(),now()))
                audit(con,"請求作成","charges",cur.lastrowid,sid,f"{target} 発表会費 {amount}円",operator); created+=1; total+=amount
            except Exception as e:
                if "UNIQUE" in str(e): skipped+=1
                else: raise
    return {"created":created,"skipped":skipped,"total":total}

def open_charges(student_id=None):
    cloud=_cloud_client()
    if cloud:
        q=cloud.table('charges').select('*,students(name,school_location)').in_('charge_status',['請求中','一部入金'])
        if student_id: q=q.eq('student_id',student_id)
        rows=q.order('target_month').execute().data; pays=cloud.table('payments').select('charge_id,amount_received,cancelled_at').execute().data
        out=[]
        for r in rows:
            r['paid']=sum(p['amount_received'] for p in pays if p['charge_id']==r['charge_id'] and not p['cancelled_at']); r['name']=r.get('students',{}).get('name',''); r['school_location']=r.get('students',{}).get('school_location','')
            if r['paid']<r['charge_amount']: out.append(r)
        return out
    sql="""SELECT c.*,s.name,s.school_location,COALESCE(SUM(CASE WHEN p.cancelled_at IS NULL THEN p.amount_received ELSE 0 END),0) paid
      FROM charges c JOIN students s USING(student_id) LEFT JOIN payments p USING(charge_id)
      WHERE c.charge_status NOT IN ('入金済','免除','取消')"""; p=[]
    if student_id: sql+=" AND c.student_id=?"; p.append(student_id)
    sql+=" GROUP BY c.charge_id HAVING paid<c.charge_amount ORDER BY c.target_month,c.charge_type"
    return [dict(r) for r in connect().execute(sql,p).fetchall()]

def _next_month(day):
    y,m=int(day[:4]),int(day[5:7])
    m+=1
    if m>12: y+=1; m=1
    return f"{y:04d}-{m:02d}"

def _evaluate_monthly_status(rows,today):
    """月謝charges（単一生徒分）から、本日時点の支払状況を1件に絞って返す。
    複数月未払いの場合は due_date が最も古いものを優先する。
    支払済みで済んでいる場合、次に払うべき月（reference_month）は、
    このアプリの前受金運用（当月中に翌月分を払う）に合わせて「今月の翌月」とする。
    reference_month以降の月謝が1件も無ければ「請求未作成」として扱う。
    """
    unpaid=[r for r in rows if r['charge_status'] in ('請求中','一部入金')]
    unpaid_with_due=[r for r in unpaid if r.get('due_date')]
    if unpaid_with_due:
        target=min(unpaid_with_due,key=lambda r:r['due_date'])
        if today>target['due_date']:
            from datetime import date
            days=(date.fromisoformat(today)-date.fromisoformat(target['due_date'])).days
            return {'state':'overdue','target_month':target['target_month'],'due_date':target['due_date'],'overdue_days':days}
        if today==target['due_date']:
            return {'state':'due_today','target_month':target['target_month'],'due_date':target['due_date'],'overdue_days':0}
        return {'state':'due_soon','target_month':target['target_month'],'due_date':target['due_date'],'overdue_days':None}
    if unpaid:
        target=min(unpaid,key=lambda r:r['target_month'])
        return {'state':'due_unset','target_month':target['target_month'],'due_date':None,'overdue_days':None}
    paid=[r for r in rows if r['charge_status'] in ('入金済','免除')]
    reference_month=_next_month(today)
    if paid:
        latest=max(paid,key=lambda r:r['target_month'])
        if latest['target_month']>=reference_month:
            return {'state':'paid','target_month':latest['target_month'],'due_date':None,'overdue_days':None}
    return {'state':'missing','target_month':reference_month,'due_date':None,'overdue_days':None}

def monthly_payment_status(student_id,today=None):
    """生徒1名分の月謝の支払状況を判定する（発表会費等は対象外）。
    戻り値: {'state':'paid'|'due_soon'|'due_today'|'overdue'|'due_unset'|'missing','target_month':'YYYY-MM',
             'due_date':'YYYY-MM-DD'|None,'overdue_days':int|None}
    'due_unset'は、未払いだが支払期限が未設定のため期限判定ができない状態
    （'due_soon'（期限前）とは区別し、期限不明であることを明示する）。
    """
    from services.common import today_jst
    today=today or today_jst()
    cloud=_cloud_client()
    if cloud:
        rows=cloud.table('charges').select('*').eq('student_id',student_id).eq('charge_type','月謝').execute().data
    else:
        rows=[dict(r) for r in connect().execute(
            "SELECT * FROM charges WHERE student_id=? AND charge_type='月謝'",(student_id,)).fetchall()]
    return _evaluate_monthly_status(rows,today)

def _due_state_label(due_date,today):
    """支払期限に対する現在の状態を日本語ラベルで返す（期限前／本日期限／期限超過／期限未設定）。"""
    if not due_date: return '期限未設定'
    if today>due_date: return '期限超過'
    if today==due_date: return '本日期限'
    return '期限前'

def unpaid(filters=None):
    from services.common import today_jst
    today=today_jst()
    cloud=_cloud_client()
    if cloud:
        filters=filters or {}; rows=open_charges(); students={s['student_id']:s for s in cloud.table('students').select('*').execute().data}; out=[]
        for c in rows:
            s=students[c['student_id']]; r={'charge_id':c['charge_id'],'name':s['name'],'school_location':s['school_location'],'enrollment_status':s['enrollment_status'],'target_month':c['target_month'],'charge_type':c['charge_type'],'charge_amount':c['charge_amount'],'paid':c['paid'],'unpaid':c['charge_amount']-c['paid'],'due_date':c.get('due_date'),'charge_status':c['charge_status'],'状態':_due_state_label(c.get('due_date'),today),'notes':c.get('notes','')}
            if filters.get('target_month') and r['target_month']!=filters['target_month']: continue
            if filters.get('school') and r['school_location']!=filters['school']: continue
            if filters.get('charge_type') and r['charge_type']!=filters['charge_type']: continue
            if filters.get('enrollment_status') and r['enrollment_status']!=filters['enrollment_status']: continue
            if filters.get('state')=='未入金' and r['paid']!=0: continue
            if filters.get('state')=='一部入金' and r['paid']==0: continue
            if filters.get('state')=='期限超過' and (not r['due_date'] or r['due_date']>=__import__('datetime').date.today().isoformat()): continue
            out.append(r)
        return out
    filters=filters or {}; sql="""SELECT c.charge_id,s.name,s.school_location,s.enrollment_status,c.target_month,c.charge_type,
      c.charge_amount,COALESCE(SUM(CASE WHEN p.cancelled_at IS NULL THEN p.amount_received ELSE 0 END),0) paid,
      c.charge_amount-COALESCE(SUM(CASE WHEN p.cancelled_at IS NULL THEN p.amount_received ELSE 0 END),0) unpaid,
      c.due_date,c.charge_status,c.notes FROM charges c JOIN students s USING(student_id) LEFT JOIN payments p USING(charge_id)
      WHERE c.charge_status NOT IN ('入金済','免除','取消')"""; p=[]
    for key,col in [('target_month','c.target_month'),('school','s.school_location'),('charge_type','c.charge_type'),('enrollment_status','s.enrollment_status')]:
        if filters.get(key): sql+=f" AND {col}=?"; p.append(filters[key])
    sql+=" GROUP BY c.charge_id HAVING unpaid>0 ORDER BY c.target_month,s.name"
    rows=[dict(r) for r in connect().execute(sql,p).fetchall()]
    if filters.get('state')=='未入金': rows=[r for r in rows if r['paid']==0]
    if filters.get('state')=='一部入金': rows=[r for r in rows if r['paid']>0]
    if filters.get('state')=='期限超過':
        from datetime import date
        rows=[r for r in rows if r['due_date'] and r['due_date']<date.today().isoformat()]
    for r in rows: r['状態']=_due_state_label(r.get('due_date'),today)
    return rows
