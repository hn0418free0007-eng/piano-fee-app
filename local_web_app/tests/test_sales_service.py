from services.student_service import save_student
from services.charge_service import create_monthly, open_charges
from services.payment_service import register_payment
from services.sales_service import (monthly_billed_amount, monthly_received_amount,
  yearly_billed_amount, yearly_received_amount,
  student_yearly_billed_amount, student_yearly_received_amount)

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
