from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo
from database import connect, now

_JST=ZoneInfo('Asia/Tokyo')

def today_jst():
    """date.today()やDBサーバーのcurrent_dateに依存せず、Asia/Tokyo基準の当日をYYYY-MM-DDで返す。"""
    return datetime.now(_JST).date().isoformat()

def previous_month_end(target_month):
    """target_month('YYYY-MM')の前月末日をdateで返す（教室の「前月末までに支払う」ルール用）。
    月末日数・うるう年はcalendar.monthrangeにより正しく計算される。"""
    y,m=int(target_month[:4]),int(target_month[5:7])
    m-=1
    if m<1: y-=1; m=12
    return date(y,m,monthrange(y,m)[1])

def shift_month(year_month,n):
    """'YYYY-MM'にnか月を加減した'YYYY-MM'を返す（年またぎ・マイナスも可）。"""
    y,m=int(year_month[:4]),int(year_month[5:7])
    idx=y*12+(m-1)+n
    return f"{idx//12:04d}-{idx%12+1:02d}"

def next_jan31(today=None):
    """本日を基準に「次に来る1月31日」をdateで返す。1月中はその年の1月31日、2月以降は翌年の1月31日。"""
    today=today or today_jst()
    y,m=int(today[:4]),int(today[5:7])
    return date(y,1,31) if m==1 else date(y+1,1,31)

def audit(con, action, table, target_id, student_id, detail, operator):
    con.execute("""INSERT INTO audit_logs(action_type,target_table,target_id,student_id,action_detail,operator_name,action_datetime)
                 VALUES(?,?,?,?,?,?,?)""", (action,table,target_id,student_id,detail,operator or "未設定",now()))

