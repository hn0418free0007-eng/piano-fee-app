"""外部設定なしで、実画面の1ボタンから履歴・売上・出力まで確認する受入テスト。"""
import os,tempfile,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

tmp=Path(tempfile.gettempdir())/'piano_fee_demo_acceptance.db'
if tmp.exists(): tmp.unlink()
os.environ['PIANO_DB_PATH']=str(tmp)

from database import init_db,connect
from services.charge_service import create_monthly
from services.sales_service import monthly_received_amount
from services.export_service import to_csv,to_excel
from services.common import today_jst
from streamlit.testing.v1 import AppTest

init_db(); today=today_jst(); month=today[:7]; create_monthly(month,today,'受入試験')
app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
assert not app.exception
assert any('今日のレッスン' in x.value for x in app.title)
buttons=[x for x in app.button if x.label=='受領・押印済み']
assert buttons, '受領・押印済みボタンが表示されません'
buttons[0].click().run(); assert not app.exception
with connect() as con:
    payment=con.execute("SELECT * FROM payments ORDER BY payment_id DESC LIMIT 1").fetchone()
    assert payment and payment['stamp_confirmed']==1 and payment['payment_status']=='処理完了'
    charge=con.execute("SELECT charge_status FROM charges WHERE charge_id=?",(payment['charge_id'],)).fetchone()
    assert charge['charge_status']=='入金済'
rows=monthly_received_amount(month); assert rows and sum(r['金額'] for r in rows)>0
assert to_csv(rows).startswith(b'\xef\xbb\xbf') and to_excel(rows).startswith(b'PK')
print(f"DEMO_OK lessons={len(app.title)} payment_id={payment['payment_id']} sales={sum(r['金額'] for r in rows)} csv=OK excel=OK")
try: tmp.unlink(missing_ok=True)
except PermissionError: pass  # WindowsではAppTest終了まで読取ハンドルが残ることがある
