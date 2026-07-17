from __future__ import annotations
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import streamlit as st

_PKCE_TTL_SECONDS = 10 * 60
_PKCE_DB_PATH = Path(os.environ.get(
    'PIANO_PKCE_DB_PATH', Path(__file__).resolve().parents[1] / 'data' / 'oauth_pkce.db'
))
_CODE_VERIFIER_SUFFIX = '-code-verifier'

class AuthCallbackError(Exception):
    """OAuthコールバックを安全な一般メッセージで失敗させる。"""

def _flow_hash(flow_id):
    return hashlib.sha256(flow_id.encode('utf-8')).hexdigest()

def _pkce_connect():
    _PKCE_DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(_PKCE_DB_PATH,timeout=5)
    con.execute('PRAGMA busy_timeout=5000')
    con.execute('''CREATE TABLE IF NOT EXISTS oauth_pkce_flows (
      flow_hash TEXT PRIMARY KEY, code_verifier TEXT NOT NULL, created_at INTEGER NOT NULL
    )''')
    return con

def _save_code_verifier(flow_id,code_verifier):
    if not flow_id or not code_verifier: raise ValueError('PKCE flow data is required')
    stamp=int(time.time())
    with _pkce_connect() as con:
        con.execute('DELETE FROM oauth_pkce_flows WHERE created_at < ?', (stamp-_PKCE_TTL_SECONDS,))
        con.execute('INSERT OR REPLACE INTO oauth_pkce_flows(flow_hash,code_verifier,created_at) VALUES(?,?,?)',
          (_flow_hash(flow_id),code_verifier,stamp))

def _load_code_verifier(flow_id):
    if not flow_id: return None
    stamp=int(time.time())
    with _pkce_connect() as con:
        con.execute('DELETE FROM oauth_pkce_flows WHERE created_at < ?', (stamp-_PKCE_TTL_SECONDS,))
        row=con.execute('SELECT code_verifier FROM oauth_pkce_flows WHERE flow_hash=?',
          (_flow_hash(flow_id),)).fetchone()
    return row[0] if row else None

def _delete_code_verifier(flow_id):
    if not flow_id: return
    with _pkce_connect() as con:
        con.execute('DELETE FROM oauth_pkce_flows WHERE flow_hash=?',(_flow_hash(flow_id),))

class _PkceFlowStorage:
    """SupabaseのPKCE verifierだけを外部リダイレクト越しに保持する。"""
    def __init__(self,flow_id): self.flow_id=flow_id; self.memory={}
    def get_item(self,key):
        if key.endswith(_CODE_VERIFIER_SUFFIX): return _load_code_verifier(self.flow_id)
        return self.memory.get(key)
    def set_item(self,key,value):
        if key.endswith(_CODE_VERIFIER_SUFFIX): _save_code_verifier(self.flow_id,value)
        else: self.memory[key]=value
    def remove_item(self,key):
        if key.endswith(_CODE_VERIFIER_SUFFIX): _delete_code_verifier(self.flow_id)
        else: self.memory.pop(key,None)

def settings():
    try: return dict(st.secrets)
    except Exception: return {}

def is_cloud_configured():
    s=settings(); return bool(s.get('supabase',{}).get('url') and s.get('supabase',{}).get('anon_key'))

def _create_client(storage=None):
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    s=settings()['supabase']
    options=SyncClientOptions(flow_type='pkce',storage=storage) if storage else None
    return create_client(s['url'],s['anon_key'],options=options)

def get_client():
    if not is_cloud_configured(): return None
    if st.session_state.get('_supabase_client') is not None:
        return st.session_state._supabase_client
    client=_create_client()
    session=st.session_state.get('supabase_session')
    if session: client.auth.set_session(session['access_token'],session['refresh_token'])
    st.session_state._supabase_client=client
    return client

def handle_callback():
    if not is_cloud_configured() or 'code' not in st.query_params: return
    code=str(st.query_params.get('code','')).strip()
    flow_id=str(st.query_params.get('oauth_flow','')).strip()
    storage=_PkceFlowStorage(flow_id)
    try:
        verifier=storage.get_item(_CODE_VERIFIER_SUFFIX)
        if not code or not flow_id or not verifier: raise AuthCallbackError()
        redirect=_redirect_url(flow_id)
        client=_create_client(storage)
        result=client.auth.exchange_code_for_session({'auth_code':code,'code_verifier':verifier,'redirect_to':redirect})
        session=result.session
        if not session or not session.user: raise AuthCallbackError()
        st.session_state.supabase_session={'access_token':session.access_token,'refresh_token':session.refresh_token,
          'provider_token':getattr(session,'provider_token',None),'email':session.user.email}
        st.session_state._supabase_client=client
    except Exception as exc:
        raise AuthCallbackError('ログインを完了できませんでした。もう一度ログインしてください。') from exc
    finally:
        storage.remove_item(_CODE_VERIFIER_SUFFIX)
        st.query_params.clear()
    st.rerun()

def _redirect_url(flow_id):
    public_url=settings().get('app',{}).get('public_url','http://127.0.0.1:8501')
    parts=urlsplit(public_url); query=dict(parse_qsl(parts.query,keep_blank_values=True))
    query['oauth_flow']=flow_id
    return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),parts.fragment))

def login_url():
    flow_id=secrets.token_urlsafe(32); storage=_PkceFlowStorage(flow_id)
    client=_create_client(storage); redirect=_redirect_url(flow_id)
    result=client.auth.sign_in_with_oauth({'provider':'google','options':{'redirect_to':redirect,
      'scopes':'openid email profile https://www.googleapis.com/auth/calendar.readonly',
      'query_params':{'access_type':'offline','prompt':'consent'}}})
    return result.url

def current_user(): return st.session_state.get('supabase_session')

def is_allowed_user(user=None):
    user=user or current_user()
    if not user: return False
    allowed=[str(x).strip().lower() for x in settings().get('app',{}).get('allowed_emails',[]) if str(x).strip()]
    return bool(allowed) and str(user.get('email','')).strip().lower() in allowed

def logout():
    c=get_client()
    if c:
        try: c.auth.sign_out()
        except Exception: pass
    st.session_state.pop('supabase_session',None)
    st.session_state.pop('_supabase_client',None)
