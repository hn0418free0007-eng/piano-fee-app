from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def _open_monthly(app):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if '月次請求' in o][0]
    radios[0].set_value(option).run()

def test_monthly_screen_uses_new_label_not_old_one(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _open_monthly(app)
    assert not app.exception,app.exception
    labels=[w.label for w in app.selectbox]
    assert 'レッスン料の対象月' in labels
    assert '対象年月' not in labels
