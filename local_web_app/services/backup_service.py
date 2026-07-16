from pathlib import Path
from datetime import datetime, date
import sqlite3
from database import DB_PATH, BASE_DIR, connect, now
from services.common import audit

def create_backup(operator="システム"):
    dest_dir=BASE_DIR/'backup'; dest_dir.mkdir(exist_ok=True)
    dest=dest_dir/f"lesson_fee_{datetime.now():%Y%m%d_%H%M%S}.db"
    with connect() as src, sqlite3.connect(dest) as out: src.backup(out)
    files=sorted(dest_dir.glob('lesson_fee_*.db'),reverse=True)
    for old in files[30:]: old.unlink()
    with connect() as con:
        audit(con,"バックアップ作成","database",None,None,dest.name,operator)
        con.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('last_auto_backup',?)",(date.today().isoformat(),))
    return dest

def auto_backup():
    if not DB_PATH.exists(): return None
    with connect() as con:
        row=con.execute("SELECT value FROM app_settings WHERE key='last_auto_backup'").fetchone()
    return None if row and row[0]==date.today().isoformat() else create_backup()

