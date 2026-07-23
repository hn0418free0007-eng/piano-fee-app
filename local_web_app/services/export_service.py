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
    # 月別・年間の集計は、いずれもreceived_date（実際に受領した日）基準。target_month（請求対象月）基準の
    # 出力が必要な場合は services/sales_service.py の *_billed_amount() を使う画面（売上管理）を利用する。
    sqls={
      '生徒一覧':"SELECT * FROM students ORDER BY name",
      '入金履歴':"SELECT * FROM payments ORDER BY received_date DESC,received_time DESC",
      '操作履歴':"SELECT * FROM audit_logs ORDER BY action_datetime DESC",
      '受領月別一覧（受領日基準）':"SELECT substr(received_date,1,7) 受領年月,SUM(amount_received) 受領金額,COUNT(*) 件数 FROM payments WHERE cancelled_at IS NULL GROUP BY substr(received_date,1,7) ORDER BY 受領年月",
      '受領年別一覧（受領日基準）':"SELECT substr(received_date,1,4) 受領年,SUM(amount_received) 受領金額,COUNT(*) 件数 FROM payments WHERE cancelled_at IS NULL GROUP BY substr(received_date,1,4) ORDER BY 受領年"
    }
    return query(sqls[kind])

