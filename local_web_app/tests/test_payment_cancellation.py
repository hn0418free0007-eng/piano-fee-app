from types import SimpleNamespace

import pytest

from database import query
from services.student_service import save_student
from services.charge_service import create_monthly, open_charges
from services.payment_service import register_payment, cancel_payment
from services.sales_service import daily_received_amount, monthly_billed_amount, monthly_received_amount

FEE = 10000

def _setup_student(operator="試験"):
    return save_student(dict(name="取消検証 生徒", school_location="中央教室", grade="小学1年",
      monthly_fee=FEE, recital_fee=15000, enrollment_date="2026-04-01", withdrawal_date=None,
      enrollment_status="在籍", guardian_name="", phone="", email="", notes=""), operator)

def _charge_for(sid, target_month):
    charges = {c["target_month"]: c for c in open_charges(sid)}
    return charges[target_month]

def test_cancel_keeps_row_and_sets_cancelled_fields(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")

    cancel_payment(pid, "入力ミス", "試験")

    rows = query("SELECT * FROM payments WHERE payment_id=?", (pid,))
    assert len(rows) == 1  # 物理削除されていない
    row = rows[0]
    assert row["cancelled_at"] is not None
    assert row["cancellation_reason"] == "入力ミス"
    assert row["payment_status"] == "取消"

def test_cancel_excludes_from_today_and_monthly_aggregates(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")

    assert daily_received_amount("2026-07-10") == FEE
    assert sum(r["金額"] for r in monthly_billed_amount("2026-07")) == FEE
    assert sum(r["金額"] for r in monthly_received_amount("2026-07")) == FEE

    cancel_payment(pid, "入力ミス", "試験")

    assert daily_received_amount("2026-07-10") == 0
    assert sum(r["金額"] for r in monthly_billed_amount("2026-07")) == 0
    assert sum(r["金額"] for r in monthly_received_amount("2026-07")) == 0

def test_cancel_reverts_charge_to_unpaid_when_only_payment_is_cancelled(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")
    assert query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"] == "入金済"

    cancel_payment(pid, "入力ミス", "試験")

    assert query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"] == "請求中"

def test_cancel_reverts_charge_to_partial_when_another_payment_remains(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    p1 = register_payment(charge["charge_id"], 4000, "2026-07-05", "現金", "試験")
    register_payment(charge["charge_id"], 6000, "2026-07-10", "現金", "試験")
    assert query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"] == "入金済"

    cancel_payment(p1, "一部取消", "試験")

    assert query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"] == "一部入金"

def test_cancel_twice_raises_value_error(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")

    cancel_payment(pid, "1回目", "試験")
    with pytest.raises(ValueError, match="有効な入金が見つかりません"):
        cancel_payment(pid, "2回目", "試験")

def test_cancel_requires_non_empty_reason(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")
    with pytest.raises(ValueError, match="取消理由"):
        cancel_payment(pid, "   ", "試験")

def test_reregistration_allowed_after_cancellation(isolated_db):
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    pid = register_payment(charge["charge_id"], FEE, "2026-07-10", "現金", "試験")

    # 取消前は、この請求はopen_chargesに現れない（すでに入金済のため）
    assert charge["charge_id"] not in [c["charge_id"] for c in open_charges(sid)]

    cancel_payment(pid, "入力ミス", "試験")

    # 取消後は未収へ戻り、再び受付対象になる
    reopened = [c for c in open_charges(sid) if c["charge_id"] == charge["charge_id"]]
    assert reopened and reopened[0]["paid"] == 0

    new_pid = register_payment(charge["charge_id"], FEE, "2026-07-11", "現金", "試験")
    assert new_pid != pid
    assert query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"] == "入金済"


# --- ローカルSQLiteとSupabaseクラウド分岐の一致確認 ---

class _FakeTable:
    """payments/charges/audit_logsの.select/.eq/.is_/.update/.insert/.execute()を最小限に模倣する。
    同じ辞書オブジェクトを参照し続けることで、.update()の変更が以後のクエリにも反映される。"""
    def __init__(self, rows, all_rows_ref):
        self._rows = rows
        self._all = all_rows_ref
        self._pending_update = None
    def select(self, *_a, **_k): return self
    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]; return self
    def is_(self, col, val):
        want_null = (val == 'null')
        self._rows = [r for r in self._rows if (r.get(col) is None) == want_null]; return self
    def update(self, payload):
        self._pending_update = payload; return self
    def insert(self, payload):
        row = dict(payload); self._all.append(row); self._rows = [row]; return self
    def execute(self):
        if self._pending_update is not None:
            for r in self._rows: r.update(self._pending_update)
        return SimpleNamespace(data=self._rows)

class _FakeClient:
    def __init__(self, tables): self._tables = tables  # dict: name -> list[dict] (shared, mutable)
    def table(self, name):
        return _FakeTable(list(self._tables.setdefault(name, [])), self._tables[name])

def test_cancel_payment_cloud_branch_matches_local_branch(isolated_db, monkeypatch):
    """
    同一シナリオ（4000円+6000円の分割入金、後から4000円分を取消）に対して、
    ローカルSQLite経路とSupabaseクラウド経路（フェイククライアント）が
    同じ最終状態（charge_status、有効な入金合計）になることを検証する。
    """
    sid = _setup_student()
    create_monthly("2026-07", "2026-07-27", "試験")
    charge = _charge_for(sid, "2026-07")
    p1 = register_payment(charge["charge_id"], 4000, "2026-07-05", "現金", "試験")
    register_payment(charge["charge_id"], 6000, "2026-07-10", "現金", "試験")
    cancel_payment(p1, "一部取消", "試験")

    local_status = query("SELECT charge_status FROM charges WHERE charge_id=?", (charge["charge_id"],))[0]["charge_status"]
    local_remaining = daily_received_amount("2026-07-10")
    assert local_status == "一部入金" and local_remaining == 6000

    tables = {
        "payments": [
            {"payment_id": 1, "charge_id": 100, "student_id": sid, "amount_received": 4000,
             "charge_amount": 10000, "cancelled_at": None},
            {"payment_id": 2, "charge_id": 100, "student_id": sid, "amount_received": 6000,
             "charge_amount": 10000, "cancelled_at": None},
        ],
        "charges": [{"charge_id": 100, "charge_status": "入金済"}],
        "audit_logs": [],
    }
    fake_client = _FakeClient(tables)
    import services.payment_service as payment_service
    monkeypatch.setattr(payment_service, "_cloud_client", lambda: fake_client)

    cancel_payment(1, "一部取消", "試験")

    cloud_payment = [r for r in tables["payments"] if r["payment_id"] == 1][0]
    cloud_charge = tables["charges"][0]
    assert cloud_payment["cancelled_at"] is not None
    assert cloud_charge["charge_status"] == local_status == "一部入金"
    remaining_cloud = sum(r["amount_received"] for r in tables["payments"] if r["cancelled_at"] is None)
    assert remaining_cloud == 6000 == local_remaining
    assert len(tables["audit_logs"]) == 1
