from io import BytesIO
import csv, io
import pandas as pd
from database import query

def to_csv(rows):
    if not rows: return b''
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    return ('\ufeff'+s.getvalue()).encode('utf-8')

def to_excel(rows,sheet_name='一覧'):
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as writer: pd.DataFrame(rows).to_excel(writer,index=False,sheet_name=sheet_name[:31])
    return out.getvalue()

def dataset(kind):
    sqls={
      '生徒一覧':"SELECT * FROM students ORDER BY name",
      '入金履歴':"SELECT * FROM payments ORDER BY received_date DESC,received_time DESC",
      '操作履歴':"SELECT * FROM audit_logs ORDER BY action_datetime DESC",
      '月別売上一覧':"SELECT substr(received_date,1,7) 年月,SUM(amount_received) 売上額,COUNT(*) 件数 FROM payments WHERE cancelled_at IS NULL GROUP BY substr(received_date,1,7) ORDER BY 年月",
      '年間売上一覧':"SELECT substr(received_date,1,4) 年,SUM(amount_received) 売上額,COUNT(*) 件数 FROM payments WHERE cancelled_at IS NULL GROUP BY substr(received_date,1,4) ORDER BY 年"
    }
    return query(sqls[kind])

