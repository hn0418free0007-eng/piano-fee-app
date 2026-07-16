from __future__ import annotations
import sqlite3
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PIANO_DB_PATH",BASE_DIR / "data" / "lesson_fee.db"))

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS students (
 student_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
 school_location TEXT NOT NULL DEFAULT '', grade TEXT NOT NULL DEFAULT '',
 monthly_fee INTEGER NOT NULL DEFAULT 0, recital_fee INTEGER NOT NULL DEFAULT 0,
 enrollment_date TEXT, withdrawal_date TEXT, enrollment_status TEXT NOT NULL DEFAULT '在籍'
  CHECK(enrollment_status IN ('在籍','休会','退会')),
 guardian_name TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT '', notes TEXT DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS charges (
 charge_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
 target_month TEXT NOT NULL, charge_type TEXT NOT NULL CHECK(charge_type IN ('月謝','発表会費','教材費','その他')),
 charge_amount INTEGER NOT NULL CHECK(charge_amount>=0), due_date TEXT,
 charge_status TEXT NOT NULL DEFAULT '請求中' CHECK(charge_status IN ('未請求','請求中','一部入金','入金済','免除','取消')),
 notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 FOREIGN KEY(student_id) REFERENCES students(student_id),
 UNIQUE(student_id,target_month,charge_type)
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id INTEGER PRIMARY KEY AUTOINCREMENT, charge_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
 student_name TEXT NOT NULL, target_month TEXT NOT NULL, payment_type TEXT NOT NULL,
 charge_amount INTEGER NOT NULL, amount_received INTEGER NOT NULL CHECK(amount_received>0),
 received_date TEXT NOT NULL, received_time TEXT NOT NULL, payment_method TEXT NOT NULL,
 received_by TEXT NOT NULL, stamp_confirmed INTEGER NOT NULL DEFAULT 0,
 stamp_confirmed_at TEXT, stamp_confirmed_by TEXT, payment_status TEXT NOT NULL DEFAULT '受領済・印鑑未確認',
 notes TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 cancelled_at TEXT, cancellation_reason TEXT,
 FOREIGN KEY(charge_id) REFERENCES charges(charge_id), FOREIGN KEY(student_id) REFERENCES students(student_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
 log_id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT NOT NULL, target_table TEXT NOT NULL,
 target_id INTEGER, student_id INTEGER, action_detail TEXT NOT NULL,
 operator_name TEXT NOT NULL, action_datetime TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS calendar_mappings (
 normalized_title TEXT PRIMARY KEY, student_id INTEGER NOT NULL, original_title TEXT NOT NULL,
 created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 FOREIGN KEY(student_id) REFERENCES students(student_id)
);
CREATE INDEX IF NOT EXISTS idx_charges_month ON charges(target_month,charge_status);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(received_date,payment_status);
DROP INDEX IF EXISTS idx_one_complete_payment;
"""

def now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def connect(path: Path | str | None = None) -> sqlite3.Connection:
    db = Path(path) if path else DB_PATH
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    return con

def init_db(path: Path | str | None = None, seed: bool = True) -> None:
    with connect(path) as con:
        con.executescript(SCHEMA)
        if seed and con.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            stamp = now()
            rows = [
                ("さくら みらい","中央教室","小学2年",9000,15000,"2025-04-01"),
                ("あおぞら かなで","東教室","小学5年",11000,15000,"2024-04-01"),
                ("ひかり おと","中央教室","中学1年",12000,18000,"2023-04-01"),
                ("こもれび りずむ","西教室","年長",8000,12000,"2026-04-01"),
                ("ほしぞら めろでぃ","東教室","高校1年",14000,18000,"2022-04-01"),
            ]
            con.executemany("""INSERT INTO students(name,school_location,grade,monthly_fee,recital_fee,enrollment_date,
                enrollment_status,created_at,updated_at) VALUES(?,?,?,?,?,?,'在籍',?,?)""",
                [r + (stamp, stamp) for r in rows])

def query(sql: str, params=(), path=None):
    with connect(path) as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]

if __name__ == "__main__":
    init_db()
    print(f"データベースを初期化しました: {DB_PATH}")
