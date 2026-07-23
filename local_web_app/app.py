import streamlit as st
from database import init_db
from services.auth_service import AuthCallbackError,is_cloud_configured,handle_callback,current_user,login_url,logout,is_allowed_user
from services.backup_service import auto_backup
from app_pages import v3_today,management,reports,payment_entry,sales
from branding import APP_ICON,APP_NAME,APP_SUBTITLE,MENU_ICONS,MENU_PAGES,OPERATOR_ROLES

st.set_page_config(page_title=APP_NAME,page_icon=APP_ICON,layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
:root{--brand-border:#e5e7eb;--brand-muted:#6b7280}
.block-container{max-width:960px;padding:1.25rem 1rem}
.stButton>button{min-height:3.2rem;font-size:1.05rem;font-weight:600;border-radius:10px}
[data-testid=stMetric]{border:1px solid var(--brand-border);border-radius:12px;padding:14px 16px;background:#fafafa}
[data-testid=stMetricLabel]{font-size:.8rem;color:var(--brand-muted)}
[data-testid=stMetricValue]{font-size:1.5rem;font-weight:700}
[data-testid=stSidebar]{width:270px!important}
[data-testid=stSidebar] .block-container{padding-top:1.5rem}
.sidebar-heading{font-size:.72rem;font-weight:700;letter-spacing:.06em;color:var(--brand-muted);text-transform:uppercase;margin:.9rem 0 .35rem}
.empty-state{border:1px solid var(--brand-border);border-radius:12px;padding:2.25rem 1rem;text-align:center;background:#fafafa}
.empty-state .icon{font-size:2rem}
.empty-state .title{margin:.5rem 0 0;font-weight:600}
.empty-state .hint{margin:.25rem 0 0;color:var(--brand-muted);font-size:.9rem}
@media(prefers-color-scheme:dark){
[data-testid=stMetric],.empty-state{background:#1c1c1c;border-color:#333}
}
@media(max-width:640px){.block-container{padding:.6rem}.stColumn{min-width:46%!important}h1{font-size:1.7rem!important}h2{font-size:1.35rem!important}[data-testid=stSidebar]{width:100%!important}}
</style>""",unsafe_allow_html=True)
init_db()
try: auto_backup()
except Exception: pass

if is_cloud_configured():
    try: handle_callback()
    except AuthCallbackError: st.error("ログインを完了できませんでした。もう一度Googleでログインしてください。")
    except Exception: st.error("ログイン処理で問題が発生しました。もう一度Googleでログインしてください。")
    if not current_user():
        st.title(f"{APP_ICON} {APP_NAME}"); st.caption(APP_SUBTITLE)
        st.write("先生用Googleアカウントでログインしてください。")
        st.link_button("Googleでログイン",login_url(),type="primary",use_container_width=True); st.stop()
    if not is_allowed_user():
        email=current_user().get('email','不明')
        logout(); st.error(f"このGoogleアカウント（{email}）は利用を許可されていません。管理者へ連絡してください。"); st.stop()

if 'v3_page' not in st.session_state: st.session_state.v3_page=MENU_PAGES[0]
with st.sidebar:
    st.title(f"{APP_ICON} {APP_NAME}")
    st.caption(APP_SUBTITLE)
    if not current_user(): st.caption("デモ・ローカルモード")
    st.divider()
    operator=st.selectbox("担当者",OPERATOR_ROLES)
    st.markdown('<p class="sidebar-heading">メニュー</p>',unsafe_allow_html=True)
    page=st.radio("メニュー",MENU_PAGES,index=MENU_PAGES.index(st.session_state.v3_page),
      format_func=lambda k:f"{MENU_ICONS[k]} {k}",label_visibility="collapsed")
    st.session_state.v3_page=page
    if current_user():
        st.divider()
        if st.button("🚪 ログアウト",use_container_width=True): logout(); st.rerun()

if page=='今日の受付': v3_today.render(operator)
elif page=='生徒管理': management.render_students(operator)
elif page=='月次請求': management.render_monthly(operator)
elif page=='発表会費請求': management.render_recital(operator)
elif page=='売上管理': sales.render()
elif page=='未入金一覧': reports.render_unpaid()
elif page=='例外処理': payment_entry.render(operator); st.divider(); reports.render_history(operator)
elif page=='データ・バックアップ': reports.render_exports(operator)
