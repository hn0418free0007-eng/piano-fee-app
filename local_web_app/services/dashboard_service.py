from datetime import date
from database import connect

def metrics(month=None):
    month=month or date.today().strftime('%Y-%m'); today=date.today().isoformat()
    with connect() as con:
        charges=con.execute("SELECT COALESCE(SUM(charge_amount),0) FROM charges WHERE target_month=? AND charge_status NOT IN ('免除','取消')",(month,)).fetchone()[0]
        paid=con.execute("SELECT COALESCE(SUM(amount_received),0) FROM payments WHERE target_month=? AND cancelled_at IS NULL",(month,)).fetchone()[0]
        unpaid_people=con.execute("""SELECT COUNT(DISTINCT c.student_id) FROM charges c LEFT JOIN (SELECT charge_id,SUM(amount_received) paid FROM payments WHERE cancelled_at IS NULL GROUP BY charge_id) p USING(charge_id) WHERE c.target_month=? AND c.charge_status NOT IN ('免除','取消') AND COALESCE(p.paid,0)<c.charge_amount""",(month,)).fetchone()[0]
        pending=con.execute("SELECT COUNT(DISTINCT student_id) FROM payments WHERE stamp_confirmed=0 AND cancelled_at IS NULL").fetchone()[0]
        partial=con.execute("SELECT COUNT(DISTINCT student_id) FROM charges WHERE target_month=? AND charge_status='一部入金'",(month,)).fetchone()[0]
        td=con.execute("SELECT COUNT(*),COALESCE(SUM(amount_received),0) FROM payments WHERE received_date=? AND cancelled_at IS NULL",(today,)).fetchone()
        recital=con.execute("SELECT COUNT(DISTINCT student_id) FROM charges WHERE target_month=? AND charge_type='発表会費' AND charge_status NOT IN ('入金済','免除','取消')",(month,)).fetchone()[0]
    return dict(charged=charges,paid=paid,unpaid=max(charges-paid,0),unpaid_people=unpaid_people,pending_stamps=pending,partial=partial,today_count=td[0],today_amount=td[1],recital_unpaid=recital)

def today_summary():
    today=date.today().isoformat()
    with connect() as con:
        rows=[dict(r) for r in con.execute("SELECT * FROM payments WHERE received_date=? AND cancelled_at IS NULL ORDER BY received_time",(today,)).fetchall()]
    return rows

