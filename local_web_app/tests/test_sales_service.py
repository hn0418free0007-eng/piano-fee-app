from types import SimpleNamespace

from database import query
from services.student_service import save_student
from services.charge_service import create_monthly, open_charges
from services.payment_service import register_payment, cancel_payment
import services.sales_service as sales_service
from services.sales_service import (monthly_billed_amount, monthly_received_amount,
  yearly_billed_amount, yearly_received_amount,
  student_yearly_billed_amount, student_yearly_received_amount,
  daily_received_amount)

FEE = 10000

def _setup_student(operator="試験"):
    sid = save_student(dict(name="集計検証 生徒", school_location="中央教室", grade="小学1年",
      monthly_fee=FEE, recital_fee=15000, enrollment_date="2026-04-01", withdrawal_date=None,
      enrollment_status="在籍", guardian_name="", phone="", email="", notes=""), operator)
    return sid

def _charge_for(sid, target_month):
    charges = {c["target_month"]: c for c in open_charges(sid)}
    return charges[target_month]

def test_advance_and_late_payments_diverge_between_billed_and_received_basis(isolated_db):
    """
    3件の入金を用意する。
    - 6月分の請求を7月に後払いで受領（後払い）
    - 7月分の請求を7月に受領（通常どおり）
    - 8月分の請求を7月に前払いで受領（前受金）
    請求月基準（target_month）では7月は7月分の1件のみだが、
    受領月基準（received_date）では7月に受領した3件すべてが合算される。
    """
    sid = _setup_student()
    for month in ("2026-06", "2026-07", "2026-08"):
        create_monthly(month, f"{month}-27", "試験")

    june_charge = _charge_for(sid, "2026-06")
    july_charge = _charge_for(sid, "2026-07")
    august_charge = _charge_for(sid, "2026-08")

    register_payment(june_charge["charge_id"], FEE, "2026-07-05", "現金", "試験")   # 6月分の後払い
    register_payment(july_charge["charge_id"], FEE, "2026-07-10", "現金", "試験")   # 7月分の通常受領
    register_payment(august_charge["charge_id"], FEE, "2026-07-20", "現金", "試験") # 8月分の前受金

    billed = monthly_billed_amount("2026-07")
    received = monthly_received_amount("2026-07")

    assert sum(r["金額"] for r in billed) == FEE
    assert sum(r["金額"] for r in received) == FEE * 3

    # 6月・8月は請求月基準では7月に現れない
    assert sum(r["金額"] for r in monthly_billed_amount("2026-06")) == FEE
    assert sum(r["金額"] for r in monthly_billed_amount("2026-08")) == FEE
    # 受領月基準では6月・8月は0円（すべて7月に受領したため）
    assert sum(r["金額"] for r in monthly_received_amount("2026-06")) == 0
    assert sum(r["金額"] for r in monthly_received_amount("2026-08")) == 0

def test_yearly_and_student_yearly_basis_match_monthly_breakdown(isolated_db):
    sid = _setup_student()
    for month in ("2026-06", "2026-07", "2026-08"):
        create_monthly(month, f"{month}-27", "試験")
    june_charge = _charge_for(sid, "2026-06")
    july_charge = _charge_for(sid, "2026-07")
    august_charge = _charge_for(sid, "2026-08")
    register_payment(june_charge["charge_id"], FEE, "2026-07-05", "現金", "試験")
    register_payment(july_charge["charge_id"], FEE, "2026-07-10", "現金", "試験")
    register_payment(august_charge["charge_id"], FEE, "2026-07-20", "現金", "試験")

    billed_by_month = {r["月"]: r["金額"] for r in yearly_billed_amount(2026)}
    received_by_month = {r["月"]: r["金額"] for r in yearly_received_amount(2026)}
    assert billed_by_month[6] == FEE and billed_by_month[7] == FEE and billed_by_month[8] == FEE
    assert received_by_month[6] == 0 and received_by_month[7] == FEE * 3 and received_by_month[8] == 0

    student_billed = {r["月"]: r["金額"] for r in student_yearly_billed_amount(2026)}
    student_received = {r["月"]: r["金額"] for r in student_yearly_received_amount(2026)}
    assert student_billed[6] == FEE and student_billed[7] == FEE and student_billed[8] == FEE
    assert student_received[7] == FEE * 3


# --- daily_received_amount / today_received_amount（本日の受領額）---

def _charges_for_months(sid, months):
    for month in months:
        create_monthly(month, f"{month}-27", "試験")
    return {m: _charge_for(sid, m) for m in months}

def test_daily_received_amount_single_payment(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-07"])
    register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    assert daily_received_amount("2026-07-10") == FEE

def test_daily_received_amount_multiple_payments_same_day(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-06", "2026-07"])
    register_payment(charges["2026-06"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    assert daily_received_amount("2026-07-10") == FEE * 2

def test_daily_received_amount_excludes_previous_day(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-07"])
    register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-09", "現金", "試験")
    assert daily_received_amount("2026-07-10") == 0

def test_daily_received_amount_excludes_next_day(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-07"])
    register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-11", "現金", "試験")
    assert daily_received_amount("2026-07-10") == 0

def test_daily_received_amount_excludes_cancelled(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-07"])
    pid = register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    cancel_payment(pid, "テスト取消", "試験")
    assert daily_received_amount("2026-07-10") == 0

def test_daily_received_amount_decreases_after_cancellation(isolated_db):
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-06", "2026-07"])
    kept = register_payment(charges["2026-06"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    to_cancel = register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-10", "現金", "試験")
    assert daily_received_amount("2026-07-10") == FEE * 2
    cancel_payment(to_cancel, "テスト取消", "試験")
    assert daily_received_amount("2026-07-10") == FEE

def test_daily_received_amount_zero_when_no_payments(isolated_db):
    assert daily_received_amount("2026-07-10") == 0


class _FakeTable:
    """Supabase Python clientの.table().select().eq().is_().execute()を模倣するフェイク。"""
    def __init__(self, rows): self._rows = list(rows)
    def select(self, *_args, **_kwargs): return self
    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]; return self
    def is_(self, col, val):
        want_null = (val == 'null')
        self._rows = [r for r in self._rows if (r.get(col) is None) == want_null]; return self
    def execute(self): return SimpleNamespace(data=self._rows)

class _FakeClient:
    def __init__(self, rows): self._rows = rows
    def table(self, _name): return _FakeTable(self._rows)

def test_daily_received_amount_same_result_local_and_cloud_branch(isolated_db, monkeypatch):
    """
    同一データに対して、ローカルSQLite経路とSupabaseクラウド経路（フェイククライアント）が
    同じ結果を返すことを検証する。実際のSupabase接続は行わない。
    """
    sid = _setup_student()
    charges = _charges_for_months(sid, ["2026-06", "2026-07", "2026-08"])
    register_payment(charges["2026-06"]["charge_id"], FEE, "2026-07-09", "現金", "試験")   # 前日
    register_payment(charges["2026-07"]["charge_id"], FEE, "2026-07-10", "現金", "試験")   # 当日・残す
    cancelled = register_payment(charges["2026-08"]["charge_id"], FEE, "2026-07-10", "現金", "試験")  # 当日・取消
    cancel_payment(cancelled, "テスト取消", "試験")

    local_total = daily_received_amount("2026-07-10")
    assert local_total == FEE  # 前日分は除外、取消分は除外、当日1件のみ残る

    raw_rows = query("SELECT amount_received, received_date, cancelled_at FROM payments")
    fake_client = _FakeClient(raw_rows)
    monkeypatch.setattr(sales_service, "is_cloud_configured", lambda: True)
    monkeypatch.setattr(sales_service, "current_user", lambda: {"email": "teacher@example.com"})
    monkeypatch.setattr(sales_service, "get_client", lambda: fake_client)

    cloud_total = daily_received_amount("2026-07-10")
    assert cloud_total == local_total == FEE
