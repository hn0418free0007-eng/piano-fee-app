from datetime import date
import streamlit as st
from services.student_service import list_students,save_student,change_status
from services.charge_service import create_monthly,create_recital
from services.common import previous_month_end,next_jan31

def money(v): return f"{int(v):,}円"
SCHOOLS=["中央教室","東教室","西教室","オンライン"]
GRADES=["未就学","小学1年","小学2年","小学3年","小学4年","小学5年","小学6年","中学1年","中学2年","中学3年","高校1年","高校2年","高校3年","社会人"]
def month_choices():
    y=date.today().year
    return [f"{yy}-{m:02d}" for yy in range(y-1,y+2) for m in range(1,13)]
def month_label(v):
    y,m=v.split('-'); return f"{y}年{int(m)}月"

def render_students(operator):
    st.title("生徒管理")
    tab1,tab2=st.tabs(["生徒一覧・編集","新規登録"])
    with tab1:
        q=st.text_input("氏名検索"); known=sorted({s['school_location'] for s in list_students()}); school=st.selectbox("教室",[""]+known,format_func=lambda x:x or "すべて"); status=st.selectbox("在籍状況",["","在籍","休会","退会"],format_func=lambda x:x or "すべて")
        rows=list_students(q,school,status)
        for s in rows:
            with st.expander(f"{s['name']}　{s['school_location']}　{s['enrollment_status']}"):
                with st.form(f"edit{s['student_id']}"):
                    name=st.text_input("氏名",s['name']); locs=list(dict.fromkeys(SCHOOLS+[s['school_location']])); loc=st.selectbox("教室",locs,index=locs.index(s['school_location'])); grades=list(dict.fromkeys(GRADES+[s['grade']])); grade=st.selectbox("学年",grades,index=grades.index(s['grade']))
                    c=st.columns(2); mf=c[0].number_input("月謝",0,value=s['monthly_fee'],step=500); rf=c[1].number_input("発表会費",0,value=s['recital_fee'],step=500)
                    guardian=st.text_input("保護者名",s['guardian_name']); phone=st.text_input("電話",s['phone']); email=st.text_input("メール",s['email']); notes=st.text_area("備考",s['notes'])
                    es=st.selectbox("在籍状況",["在籍","休会","退会"],index=["在籍","休会","退会"].index(s['enrollment_status']))
                    if st.form_submit_button("変更を保存"):
                        save_student(dict(name=name,school_location=loc,grade=grade,monthly_fee=mf,recital_fee=rf,enrollment_date=s['enrollment_date'],withdrawal_date=s['withdrawal_date'],enrollment_status=es,guardian_name=guardian,phone=phone,email=email,notes=notes),operator,s['student_id']); st.success("保存しました"); st.rerun()
    with tab2:
        with st.form("new_student"):
            name=st.text_input("氏名（必須）"); loc=st.selectbox("教室",SCHOOLS); grade=st.selectbox("学年",GRADES)
            c=st.columns(2); mf=c[0].number_input("月謝",0,step=500); rf=c[1].number_input("発表会費",0,step=500)
            guardian=st.text_input("保護者名"); phone=st.text_input("電話"); email=st.text_input("メール"); notes=st.text_area("備考")
            if st.form_submit_button("新規登録",type="primary"):
                if not name or not loc: st.error("氏名と教室は必須です。")
                else: save_student(dict(name=name,school_location=loc,grade=grade,monthly_fee=mf,recital_fee=rf,enrollment_date=date.today().isoformat(),withdrawal_date=None,enrollment_status='在籍',guardian_name=guardian,phone=phone,email=email,notes=notes),operator); st.success("登録しました")

def render_monthly(operator):
    st.title("月次請求作成")
    months=month_choices(); current=date.today().strftime('%Y-%m'); target=st.selectbox("対象年月",months,index=months.index(current),format_func=month_label)
    if st.session_state.get('_monthly_due_target')!=target:
        st.session_state['monthly_due']=previous_month_end(target); st.session_state['_monthly_due_target']=target
    due=st.date_input("支払期限",key='monthly_due')
    st.caption("初期値は対象月の前月末です。")
    students=list_students(status='在籍'); st.info(f"対象 {len(students)}人 / 請求予定合計 {money(sum(s['monthly_fee'] for s in students))}")
    if st.checkbox("対象人数と金額を確認しました") and st.button(f"{int(target[5:])}月請求作成",type="primary",use_container_width=True):
        r=create_monthly(target,due.isoformat(),operator); st.success(f"新規作成 {r['created']}件 / 重複スキップ {r['skipped']}件 / 請求総額 {money(r['total'])}")

def render_recital(operator):
    st.title("発表会費請求")
    target=st.text_input("対象年度または開催名",f"{date.today().year}年度発表会")
    if 'recital_due' not in st.session_state: st.session_state['recital_due']=next_jan31()
    due=st.date_input("支払期限",key='recital_due')
    st.caption("初期値は次に来る1月31日です。")
    students=list_students(status='在籍'); lookup={s['student_id']:s for s in students}
    ids=st.multiselect("参加生徒（不参加者は選択しない）",lookup,format_func=lambda x:f"{lookup[x]['name']}（{money(lookup[x]['recital_fee'])}）")
    st.info(f"対象 {len(ids)}人 / 合計 {money(sum(lookup[x]['recital_fee'] for x in ids))}")
    if ids and st.checkbox("対象者を確認しました") and st.button("発表会費請求を作成",type="primary"):
        r=create_recital(ids,target,{x:lookup[x]['recital_fee'] for x in ids},due.isoformat(),operator); st.success(f"新規 {r['created']}件 / 重複 {r['skipped']}件 / {money(r['total'])}")
