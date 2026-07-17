from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
import pytest

from services import auth_service


class SessionState(dict):
    __getattr__=dict.get
    __setattr__=dict.__setitem__


class QueryParams(dict):
    pass


def fake_streamlit(query=None):
    calls=[]
    return SimpleNamespace(session_state=SessionState(),query_params=QueryParams(query or {}),
      rerun=lambda: calls.append('rerun')),calls


def test_pkce_verifier_survives_new_storage_instance(tmp_path,monkeypatch):
    monkeypatch.setattr(auth_service,'_PKCE_DB_PATH',tmp_path/'pkce.db')
    first=auth_service._PkceFlowStorage('flow-id')
    first.set_item('sb-project-code-verifier','verifier-secret')
    second=auth_service._PkceFlowStorage('flow-id')
    assert second.get_item('sb-project-code-verifier')=='verifier-secret'
    second.remove_item('sb-project-code-verifier')
    assert first.get_item('sb-project-code-verifier') is None


def test_real_supabase_client_creates_pkce_and_persists_verifier(tmp_path,monkeypatch):
    monkeypatch.setattr(auth_service,'_PKCE_DB_PATH',tmp_path/'pkce.db')
    monkeypatch.setattr(auth_service,'settings',lambda: {
      'supabase':{'url':'https://project.supabase.co','anon_key':'public-key'},
      'app':{'public_url':'https://piano.example/'}})
    oauth_url=auth_service.login_url()
    oauth_query=parse_qs(urlsplit(oauth_url).query)
    assert oauth_query['code_challenge_method']==['s256']
    redirect_to=oauth_query['redirect_to'][0]
    flow_id=parse_qs(urlsplit(redirect_to).query)['oauth_flow'][0]
    verifier=auth_service._load_code_verifier(flow_id)
    assert verifier
    assert verifier not in oauth_url


def test_callback_never_exchanges_without_verifier(tmp_path,monkeypatch):
    monkeypatch.setattr(auth_service,'_PKCE_DB_PATH',tmp_path/'pkce.db')
    fake,calls=fake_streamlit({'code':'auth-code','oauth_flow':'unknown-flow'})
    monkeypatch.setattr(auth_service,'st',fake)
    monkeypatch.setattr(auth_service,'is_cloud_configured',lambda: True)
    monkeypatch.setattr(auth_service,'_create_client',lambda storage=None: pytest.fail('exchange client must not be created'))
    with pytest.raises(auth_service.AuthCallbackError): auth_service.handle_callback()
    assert fake.query_params=={}
    assert calls==[]


def test_oauth_callback_restores_verifier_and_provider_token(tmp_path,monkeypatch):
    monkeypatch.setattr(auth_service,'_PKCE_DB_PATH',tmp_path/'pkce.db')
    fake,calls=fake_streamlit()
    monkeypatch.setattr(auth_service,'st',fake)
    monkeypatch.setattr(auth_service,'settings',lambda: {
      'supabase':{'url':'https://project.supabase.co','anon_key':'public-key'},
      'app':{'public_url':'https://piano.example/'}})

    started={}
    class Auth:
        def __init__(self,storage): self.storage=storage
        def sign_in_with_oauth(self,credentials):
            self.storage.set_item('sb-project-code-verifier','verifier-secret')
            started['redirect_to']=credentials['options']['redirect_to']
            return SimpleNamespace(url='https://accounts.example/authorize')
        def exchange_code_for_session(self,params):
            assert params['auth_code']=='auth-code'
            assert params['code_verifier']=='verifier-secret'
            assert parse_qs(urlsplit(params['redirect_to']).query)['oauth_flow']==[flow_id]
            user=SimpleNamespace(email='allowed-user')
            session=SimpleNamespace(access_token='access',refresh_token='refresh',
              provider_token='google-provider-token',user=user)
            return SimpleNamespace(session=session)

    class Client:
        def __init__(self,storage): self.auth=Auth(storage)

    monkeypatch.setattr(auth_service,'_create_client',lambda storage=None: Client(storage))
    login=auth_service.login_url()
    assert login=='https://accounts.example/authorize'
    flow_id=parse_qs(urlsplit(started['redirect_to']).query)['oauth_flow'][0]
    fake.query_params.update({'code':'auth-code','oauth_flow':flow_id})
    auth_service.handle_callback()
    assert fake.session_state.supabase_session['provider_token']=='google-provider-token'
    assert fake.query_params=={}
    assert calls==['rerun']
    assert auth_service._load_code_verifier(flow_id) is None
