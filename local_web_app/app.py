import streamlit as st
from database import init_db
from services.auth_service import AuthCallbackError,is_cloud_configured,handle_callback,current_user,login_url,logout,is_allowed_user
from services.backup_service import auto_backup
from app_pages import v3_today,management,reports,payment_entry,sales

st.set_page_config(page_title="ピアノ教室運営 Ver.3",page_icon="🎹",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:900px;padding:1rem}.stButton>button{min-height:3.4rem;font-size:1.08rem;font-weight:700;border-radius:12px}
[data-testid=stMetric]{border:1px solid #e7e7e7;border-radius:12px;padding:10px;background:#fffdf7}
@media(max-width:640px){.block-container{padding:.6rem}.stColumn{min-width:46%!important}h1{font-size:1.7rem!important}h2{font-size:1.35rem!important}}
</style>""",unsafe_allow_html=True)
init_db()
try: auto_backup()
except Exception: pass

if is_cloud_configured():
    try: handle_callback()
    except AuthCallbackError: st.error("ログインを完了できませんでした。もう一度Googleでログインしてください。")
    except Exception: st.error("ログイン処理で問題が発生しました。もう一度Googleでログインしてください。")
    if not current_user():
        st.title("🎹 ピアノ教室運営 Ver.3"); st.write("先生用Googleアカウントでログインしてください。")
        st.link_button("Googleでログイン",login_url(),type="primary",use_container_width=True); st.stop()
    if not is_allowed_user():
        email=current_user().get('email','不明')
        logout(); st.error(f"このGoogleアカウント（{email}）は利用を許可されていません。管理者へ連絡してください。"); st.stop()

PAGES=["今日の受付","生徒管理","月次請求","発表会費請求","売上管理","未入金一覧","例外処理","データ・バックアップ"]
if 'v3_page' not in st.session_state: st.session_state.v3_page='今日の受付'
with st.sidebar:
    st.title("🎹 Ver.3")
    if current_user(): st.caption(current_user().get('email','Googleログイン済み'))
    else: st.caption("デモ・ローカルモード")
    operator=st.selectbox("担当者",["先生","受付担当","代講講師"])
    page=st.radio("メニュー",PAGES,index=PAGES.index(st.session_state.v3_page)); st.session_state.v3_page=page
    if current_user() and st.button("ログアウト"): logout(); st.rerun()

if page=='今日の受付': v3_today.render(operator)
elif page=='生徒管理': management.render_students(operator)
elif page=='月次請求': management.render_monthly(operator)
elif page=='発表会費請求': management.render_recital(operator)
elif page=='売上管理': sales.render()
elif page=='未入金一覧': reports.render_unpaid()
elif page=='例外処理': payment_entry.render(operator); st.divider(); reports.render_history(operator)
elif page=='データ・バックアップ': reports.render_exports(operator)
