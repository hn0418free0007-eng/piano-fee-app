from __future__ import annotations
import streamlit as st

def settings():
    try: return dict(st.secrets)
    except Exception: return {}

def is_cloud_configured():
    s=settings(); return bool(s.get('supabase',{}).get('url') and s.get('supabase',{}).get('anon_key'))

def get_client():
    if not is_cloud_configured(): return None
    if st.session_state.get('_supabase_client') is not None:
        return st.session_state._supabase_client
    from supabase import create_client
    s=settings()['supabase']; client=create_client(s['url'],s['anon_key'])
    session=st.session_state.get('supabase_session')
    if session: client.auth.set_session(session['access_token'],session['refresh_token'])
    st.session_state._supabase_client=client
    return client

def handle_callback():
    if not is_cloud_configured() or 'code' not in st.query_params: return
    client=get_client(); redirect=settings().get('app',{}).get('public_url','http://127.0.0.1:8501')
    result=client.auth.exchange_code_for_session({'auth_code':st.query_params['code'],'redirect_to':redirect})
    session=result.session
    st.session_state.supabase_session={'access_token':session.access_token,'refresh_token':session.refresh_token,
      'provider_token':getattr(session,'provider_token',None),'email':session.user.email}
    st.query_params.clear(); st.rerun()

def login_url():
    s=settings(); client=get_client(); redirect=s.get('app',{}).get('public_url','http://127.0.0.1:8501')
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
