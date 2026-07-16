from database import connect,now
from services.auth_service import get_client,current_user,is_cloud_configured

def cloud_active(): return is_cloud_configured() and bool(current_user())

def get_mappings():
    if cloud_active(): rows=get_client().table('calendar_mappings').select('normalized_title,student_id').execute().data
    else:
        with connect() as con: rows=[dict(r) for r in con.execute('SELECT normalized_title,student_id FROM calendar_mappings').fetchall()]
    return {r['normalized_title']:r['student_id'] for r in rows}

def save_mapping(normalized_title,original_title,student_id,operator):
    if not normalized_title: raise ValueError('空の予定タイトルは紐付けできません。')
    stamp=now(); payload=dict(normalized_title=normalized_title,original_title=original_title,student_id=student_id,created_by=operator,updated_at=stamp)
    if cloud_active(): get_client().table('calendar_mappings').upsert(payload,on_conflict='normalized_title').execute()
    else:
        with connect() as con:
            con.execute("""INSERT INTO calendar_mappings(normalized_title,student_id,original_title,created_by,created_at,updated_at)
              VALUES(?,?,?,?,?,?) ON CONFLICT(normalized_title) DO UPDATE SET student_id=excluded.student_id,original_title=excluded.original_title,created_by=excluded.created_by,updated_at=excluded.updated_at""",
              (normalized_title,student_id,original_title,operator,stamp,stamp))

