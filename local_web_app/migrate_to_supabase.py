"""SQLiteを読み取り専用でSupabaseへ移行。既定はプレビュー、既存行は上書きしない。"""
from __future__ import annotations
import argparse,hashlib,os,sqlite3,sys
from pathlib import Path
from database import DB_PATH

TABLES=[('students','student_id'),('charges','charge_id'),('payments','payment_id'),('audit_logs','log_id'),('calendar_mappings','normalized_title')]
IDENTITY_TABLES=[('students','student_id'),('charges','charge_id'),('payments','payment_id'),('audit_logs','log_id')]

def source_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def preview(path=DB_PATH):
    uri=f"file:{Path(path).resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri,uri=True) as con:
        con.row_factory=sqlite3.Row; names={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {t:[dict(r) for r in con.execute(f'SELECT * FROM {t}').fetchall()] if t in names else [] for t,_ in TABLES}

def sync_identity_sequences(client):
    rows=client.rpc('sync_migration_identity_sequences').execute().data or []
    actual={(r.get('table_name'),r.get('column_name')) for r in rows}
    expected=set(IDENTITY_TABLES)
    if actual!=expected:
        missing=sorted(expected-actual); unexpected=sorted(actual-expected)
        raise RuntimeError(f'Identityシーケンス同期結果が不完全です。missing={missing}, unexpected={unexpected}')
    for row in rows:
        expected_value=row.get('max_id') if row.get('max_id') is not None else 1
        if expected_value!=row.get('sequence_value') or bool(row.get('is_called'))!=(row.get('max_id') is not None):
            raise RuntimeError(f"{row.get('table_name')}.{row.get('column_name')} のシーケンス値が最大IDと一致しません。")
        print(f"{row['table_name']}.{row['column_name']}: 最大ID {row['max_id']} / シーケンス {row['sequence_value']}")
    return rows

def migrate(client,data,fingerprint,source_name):
    summary={}; total_errors=[]
    existing_run=client.table('migration_runs').select('source_sha256').eq('source_sha256',fingerprint).execute().data
    if existing_run: raise RuntimeError('このSQLiteファイルは移行済みです。同じデータは再登録しません。')
    for table,key in TABLES:
        ok=skip=0; errors=[]
        existing=client.table(table).select(key).execute().data
        existing_ids={str(r[key]) for r in existing}
        for row in data[table]:
            if str(row[key]) in existing_ids: skip+=1; continue
            try: client.table(table).insert(row).execute(); ok+=1
            except Exception as e: errors.append(f"{key}={row.get(key)}: {e}")
        summary[table]={'registered':ok,'skipped':skip,'errors':len(errors)}; total_errors.extend(f'{table}: {x}' for x in errors)
        print(f"{table}: 登録 {ok} / 既存スキップ {skip} / エラー {len(errors)}")
        for e in errors[:5]: print(f'  {e}',file=sys.stderr)
    if not total_errors:
        try: summary['identity_sequences']=sync_identity_sequences(client)
        except Exception as e: total_errors.append(f'identity_sequences: {e}')
    if not total_errors:
        client.table('migration_runs').insert({'source_sha256':fingerprint,'source_name':source_name,'detail':summary}).execute()
    return summary,total_errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--commit',action='store_true'); ap.add_argument('--db',default=str(DB_PATH)); args=ap.parse_args()
    path=Path(args.db).resolve()
    if not path.exists(): raise SystemExit(f'SQLiteがありません: {path}')
    data=preview(path); fingerprint=source_hash(path)
    print(f'元SQLite（読み取り専用）: {path}'); print(f'SHA-256: {fingerprint}')
    for table,rows in data.items(): print(f'{table}: 移行候補 {len(rows)}件')
    if not args.commit: print('プレビューのみです。書込みは行っていません。--commit で本番確認へ進みます。'); return
    url=os.getenv('SUPABASE_URL'); key=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key: raise SystemExit('SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY を環境変数へ設定してください。')
    print('注意: 既存行は上書きせずスキップします。元SQLiteは変更しません。')
    if input('本番Supabaseへ移行します。MIGRATE と入力してください: ')!='MIGRATE': print('中止しました。'); return
    from supabase import create_client
    summary,errors=migrate(create_client(url,key),data,fingerprint,path.name)
    if errors: raise SystemExit(f'一部失敗しました。成功・スキップ件数は上記のとおりです。エラー {len(errors)}件を修正して再実行してください。')
    print('全テーブルの移行が完了し、移行済み指紋を登録しました。')
if __name__=='__main__': main()
