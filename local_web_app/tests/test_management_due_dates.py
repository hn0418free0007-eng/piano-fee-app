from datetime import date
from pathlib import Path
from streamlit.testing.v1 import AppTest
from services.common import next_jan31

ROOT=Path(__file__).resolve().parents[1]

# うるう年(2028年3月分→2028年2月29日)・年またぎの計算そのものは
# tests/test_common.py::test_previous_month_end_leap_year 等で純粋関数として検証済み。
# ここでは、日付を凍結してUI（対象月ドロップダウン・支払期限の連動）が
# 実際にそれらの計算結果通りに動くことを確認する。

def _freeze_today(monkeypatch,fixed_date):
    import app_pages.management as management
    class _FixedDate(date):
        @classmethod
        def today(cls): return fixed_date
    monkeypatch.setattr(management,'date',_FixedDate)

def _select_menu(app,page):
    radios=[w for w in app.radio if w.label=='メニュー']
    option=[o for o in radios[0].options if page in o][0]
    radios[0].set_value(option).run()

def _select_target_month(app,label):
    sb=[w for w in app.selectbox if w.label=='レッスン料の対象月'][0]
    sb.select(label).run()

def _target_month_widget(app):
    return [w for w in app.selectbox if w.label=='レッスン料の対象月'][0]

def _due_value(app):
    return [w for w in app.date_input if w.label=='支払期限'][0].value

def test_initial_selection_is_next_month(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception,app.exception
    _select_menu(app,'月次請求')
    assert _target_month_widget(app).value=='2026-08'
    assert _due_value(app)==date(2026,7,31)

def test_two_months_ahead_is_selectable(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年9月')
    # 翌々月(9月)が選択でき、期限が正しく連動することを支払期限側から確認する
    assert _due_value(app)==date(2026,8,31)

def test_past_month_within_current_year_is_selectable(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年1月')
    assert _due_value(app)==date(2025,12,31)

def test_due_date_updates_when_target_month_changes(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年8月')
    assert _due_value(app)==date(2026,7,31)
    _select_target_month(app,'2026年9月')
    assert _due_value(app)==date(2026,8,31)

def test_manual_due_date_change_is_not_reverted_by_rerun(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,7,23))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2026年8月')
    due_widget=[w for w in app.date_input if w.label=='支払期限'][0]
    due_widget.set_value(date(2026,7,25)).run()
    assert _due_value(app)==date(2026,7,25)
    # 対象月を変更していない状態で再実行しても、手動変更値が勝手に戻らない
    app.run()
    assert _due_value(app)==date(2026,7,25)

def test_december_rolls_over_to_next_year_january(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2026,12,10))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception,app.exception
    _select_menu(app,'月次請求')
    # 翌月=2027年1月が初期選択されること
    assert _target_month_widget(app).value=='2027-01'
    assert _due_value(app)==date(2026,12,31)

def test_leap_year_february_due_date_via_ui(isolated_db,monkeypatch):
    _freeze_today(monkeypatch,date(2028,2,10))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    _select_menu(app,'月次請求')
    _select_target_month(app,'2028年3月')
    assert _due_value(app)==date(2028,2,29)

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
