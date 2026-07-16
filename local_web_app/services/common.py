from database import connect, now

def audit(con, action, table, target_id, student_id, detail, operator):
    con.execute("""INSERT INTO audit_logs(action_type,target_table,target_id,student_id,action_detail,operator_name,action_datetime)
                 VALUES(?,?,?,?,?,?,?)""", (action,table,target_id,student_id,detail,operator or "未設定",now()))

