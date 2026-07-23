from datetime import date
from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.common import next_jan31

ROOT=Path(__file__).resolve().parents[1]

# うるう年（2028年3月分→2028年2月29日）の計算はmanagement.pyの対象年月ドロップダウンが
# 現在日付±1年しか選べないため、ここでは選べない。純粋な計算ロジックとしては
# tests/test_common.py::test_previous_month_end_leap_year で検証している。

def _select_menu(app,page):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if page in o][0]
    radios[0].set_value(option).run()

def _select_target_month(app,label):
    sb=[w for w in app.selectbox if w.label=='対象年月'][0]
    sb.select(label).run()

def _due_value(app):
    return [w for w in app.date_input if w.label=='支払期限'][0].value

def test_monthly_due_default_is_previous_month_end(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception,app.exception
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年8月')
    assert _due_value(app)==date(2026,7,31)

def test_monthly_due_default_handles_year_boundary(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年1月')
    assert _due_value(app)==date(2025,12,31)

def test_monthly_due_default_handles_non_leap_february(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2027年3月')
    assert _due_value(app)==date(2027,2,28)

def test_monthly_due_updates_when_target_month_changes(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年8月')
    assert _due_value(app)==date(2026,7,31)
    _select_target_month(app,'2026年9月')
    assert _due_value(app)==date(2026,8,31)

def test_monthly_due_manual_change_is_not_reverted_by_rerun(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年8月')
    due_widget=[w for w in app.date_input if w.label=='支払期限'][0]
    due_widget.set_value(date(2026,7,25)).run()
    assert _due_value(app)==date(2026,7,25)
    # 対象月を変更していない状態で再実行しても、手動変更値が勝手に戻らない
    app.run()
    assert _due_value(app)==date(2026,7,25)

def test_recital_due_default_is_next_jan31(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'発表会費請求')
    assert _due_value(app)==next_jan31()

def test_recital_due_manual_change_is_not_reverted_by_rerun(isolated_db):
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'発表会費請求')
    due_widget=[w for w in app.date_input if w.label=='支払期限'][0]
    due_widget.set_value(date(2026,3,1)).run()
    assert _due_value(app)==date(2026,3,1)
    app.run()
    assert _due_value(app)==date(2026,3,1)
