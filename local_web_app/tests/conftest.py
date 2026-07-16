import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

@pytest.fixture()
def isolated_db(tmp_path,monkeypatch):
    import database
    path=tmp_path/'test.db'; monkeypatch.setattr(database,'DB_PATH',path)
    # imported service modules call database.connect dynamically but default path is resolved there
    database.init_db(path,seed=False)
    original=database.connect
    def local_connect(p=None): return original(p or path)
    monkeypatch.setattr(database,'connect',local_connect)
    for mod in ['services.student_service','services.charge_service','services.payment_service','services.dashboard_service','services.backup_service','services.calendar_mapping_service']:
        if mod in sys.modules: monkeypatch.setattr(sys.modules[mod],'connect',local_connect)
    return path
