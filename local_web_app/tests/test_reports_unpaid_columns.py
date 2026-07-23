from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.common import now

ROOT=Path(__file__).resolve().parents[1]

def _select_menu(app,page):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if page in o][0]
    radios[0].set_value(option).run()

def _seed_unpaid_charge(student_name='さくら みらい'):
    import database
    with database.connect() as con:
        sid=con.execute("SELECT student_id FROM students WHERE name=?",(student_name,)).fetchone()['student_id']
        con.execute("""INSERT INTO charges(student_id,target_month,charge_type,charge_amount,due_date,charge_status,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?)""",(sid,'2026-08','月謝',9000,'2026-07-31','請求中',now(),now()))

def test_unpaid_list_shows_all_required_columns_in_requested_order(isolated_db):
    import database
    database.init_db(isolated_db,seed=True)
    _seed_unpaid_charge()
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception,app.exception
    _select_menu(app,'未入金一覧')
    assert not app.exception,app.exception
    df=app.dataframe[0].value
    columns=list(df.columns)
    for col in ('target_month','charge_type','charge_amount','due_date','状態'):
        assert col in columns, f"{col} が未入金一覧に表示されていない"
    # 対象月→請求種別→請求額→支払期限→状態の相対順序を確認
    positions=[columns.index(c) for c in ('target_month','charge_type','charge_amount','due_date','状態')]
    assert positions==sorted(positions), f"列順が意図通りでない: {columns}"

def test_unpaid_csv_and_excel_include_status_column(isolated_db):
    import database
    database.init_db(isolated_db,seed=True)
    _seed_unpaid_charge()
    from services.charge_service import unpaid
    from app_pages.reports import UNPAID_COLUMN_ORDER
    from services.export_service import to_csv,to_excel
    rows=unpaid()
    rows=[{k:r[k] for k in UNPAID_COLUMN_ORDER if k in r} for r in rows]
    header=to_csv(rows).decode('utf-8-sig').splitlines()[0]
    assert '状態' in header.split(',')
    assert header.split(',').index('due_date')<header.split(',').index('状態')
    import pandas as pd,io
    xdf=pd.read_excel(io.BytesIO(to_excel(rows,'未入金一覧')))
    assert '状態' in xdf.columns
