from database import connect, now
from services.common import audit

def _cloud_client():
    from services.auth_service import is_cloud_configured,current_user,get_client
    return get_client() if is_cloud_configured() and current_user() else None

def list_students(search="", school="", status=""):
    cloud=_cloud_client()
    if cloud:
        q=cloud.table('students').select('*')
        if search: q=q.ilike('name',f'%{search}%')
        if school: q=q.eq('school_location',school)
        if status: q=q.eq('enrollment_status',status)
        return q.order('name').execute().data
    sql="SELECT * FROM students WHERE name LIKE ?"; p=[f"%{search}%"]
    if school: sql+=" AND school_location=?"; p.append(school)
    if status: sql+=" AND enrollment_status=?"; p.append(status)
    return [dict(r) for r in connect().execute(sql+" ORDER BY name",p).fetchall()]

def save_student(data, operator, student_id=None):
    stamp=now()
    fields=(data["name"],data["school_location"],data["grade"],int(data["monthly_fee"]),int(data["recital_fee"]),
            data.get("enrollment_date"),data.get("withdrawal_date"),data["enrollment_status"],data.get("guardian_name",""),
            data.get("phone",""),data.get("email",""),data.get("notes",""))
    cloud=_cloud_client()
    if cloud:
        keys=['name','school_location','grade','monthly_fee','recital_fee','enrollment_date','withdrawal_date','enrollment_status','guardian_name','phone','email','notes']
        payload=dict(zip(keys,fields)); payload['updated_at']=stamp
        if student_id: sid=student_id; cloud.table('students').update(payload).eq('student_id',sid).execute()
        else: payload['created_at']=stamp; sid=cloud.table('students').insert(payload).execute().data[0]['student_id']
        cloud.table('audit_logs').insert({'action_type':'生徒情報変更','target_table':'students','target_id':sid,'student_id':sid,'action_detail':'生徒情報を保存','operator_name':operator}).execute()
        return sid
    with connect() as con:
        if student_id:
            con.execute("""UPDATE students SET name=?,school_location=?,grade=?,monthly_fee=?,recital_fee=?,enrollment_date=?,
              withdrawal_date=?,enrollment_status=?,guardian_name=?,phone=?,email=?,notes=?,updated_at=? WHERE student_id=?""", fields+(stamp,student_id))
            sid=student_id
        else:
            cur=con.execute("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
              withdrawal_date,enrollment_status,guardian_name,phone,email,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", fields+(stamp,stamp))
            sid=cur.lastrowid
        audit(con,"生徒情報変更","students",sid,sid,"生徒情報を保存",operator)
    return sid

def change_status(student_id,status,operator):
    cloud=_cloud_client()
    if cloud:
        payload={'enrollment_status':status,'updated_at':now()}
        if status=='退会': payload['withdrawal_date']=__import__('datetime').date.today().isoformat()
        cloud.table('students').update(payload).eq('student_id',student_id).execute()
        cloud.table('audit_logs').insert({'action_type':'生徒情報変更','target_table':'students','target_id':student_id,'student_id':student_id,'action_detail':f'在籍状況を{status}へ変更','operator_name':operator}).execute(); return
    with connect() as con:
        con.execute("UPDATE students SET enrollment_status=?, withdrawal_date=CASE WHEN ?='退会' THEN date('now','localtime') ELSE withdrawal_date END, updated_at=? WHERE student_id=?",(status,status,now(),student_id))
        audit(con,"生徒情報変更","students",student_id,student_id,f"在籍状況を{status}へ変更",operator)
