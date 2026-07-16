def test_backup(isolated_db,tmp_path,monkeypatch):
    import services.backup_service as b
    monkeypatch.setattr(b,'BASE_DIR',tmp_path); monkeypatch.setattr(b,'DB_PATH',isolated_db)
    dest=b.create_backup('試験'); assert dest.exists() and dest.stat().st_size>0

