from datetime import datetime
from zoneinfo import ZoneInfo
from database import connect, now

_JST=ZoneInfo('Asia/Tokyo')

def today_jst():
    """date.today()やDBサーバーのcurrent_dateに依存せず、Asia/Tokyo基準の当日をYYYY-MM-DDで返す。"""
    return datetime.now(_JST).date().isoformat()

def audit(con, action, table, target_id, student_id, detail, operator):
    con.execute("""INSERT INTO audit_logs(action_type,target_table,target_id,student_id,action_detail,operator_name,action_datetime)
                 VALUES(?,?,?,?,?,?,?)""", (action,table,target_id,student_id,detail,operator or "未設定",now()))

