from types import SimpleNamespace
from pathlib import Path

import pytest

from migrate_to_supabase import IDENTITY_TABLES,sync_identity_sequences


class RpcClient:
    def __init__(self,rows): self.rows=rows; self.called=[]
    def rpc(self,name):
        self.called.append(name)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.rows))


def sequence_rows():
    maxima={'students':5,'charges':10,'payments':3,'audit_logs':17}
    return [{'table_name':table,'column_name':column,'max_id':maxima[table],
      'sequence_value':maxima[table],'is_called':True} for table,column in IDENTITY_TABLES]


def test_syncs_all_migrated_identity_sequences():
    client=RpcClient(sequence_rows())
    rows=sync_identity_sequences(client)
    assert client.called==['sync_migration_identity_sequences']
    assert {(r['table_name'],r['column_name']) for r in rows}==set(IDENTITY_TABLES)


def test_rejects_missing_identity_sequence_result():
    client=RpcClient(sequence_rows()[:-1])
    with pytest.raises(RuntimeError,match='不完全'): sync_identity_sequences(client)


def test_rejects_sequence_that_does_not_match_max_id():
    rows=sequence_rows(); rows[2]['sequence_value']=1
    with pytest.raises(RuntimeError,match='一致しません'): sync_identity_sequences(RpcClient(rows))


def test_sequence_sync_sql_uses_identity_sequences_and_service_role_only():
    sql=(Path(__file__).resolve().parents[1]/'supabase_sequence_sync.sql').read_text(encoding='utf-8')
    assert 'pg_catalog.pg_get_serial_sequence' in sql
    assert 'pg_catalog.setval' in sql
    assert 'revoke all on function sync_migration_identity_sequences() from public' in sql
    assert 'grant execute on function sync_migration_identity_sequences() to service_role' in sql
    assert 'select * from sync_migration_identity_sequences()' in sql
    for table,column in IDENTITY_TABLES:
        assert f"('public.{table}','{column}')" in sql
