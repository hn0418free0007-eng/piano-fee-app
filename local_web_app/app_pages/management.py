from datetime import date
import pandas as pd
import streamlit as st
from services.student_service import list_students,save_student,change_status
from services.charge_service import create_monthly,create_recital,monthly_billing_eligibility
from services.common import previous_month_end,next_jan31,shift_month

def money(v): return f"{int(v):,}円"
SCHOOLS=["中央教室","東教室","西教室","オンライン"]
GRADES=["未就学","小学1年","小学2年","小学3年","小学4年","小学5年","小学6年","中学1年","中学2年","中学3年","高校1年","高校2年","高校3年","社会人"]
def month_choices(today=None):
    """当年1月から、当月の2か月先（翌々月）までを選択肢にする。
    例: 本日2026-07なら2026-01〜2026-09。"""
    today=today or date.today()
    start=f"{today.year:04d}-01"; end=shift_month(f"{today.year:04d}-{today.month:02d}",2)
    months=[]; cur=start
    while cur<=end: months.append(cur); cur=shift_month(cur,1)
    return months
def month_label(v):
    y,m=v.split('-'); return f"{y}年{int(m)}月"
def _final_billing_month_choices(ref_date):
    """退会日を中心に前後1年、計3年分の月を選択肢にする。"""
    start=f"{ref_date.year-1:04d}-01"; end=f"{ref_date.year+1:04d}-12"
    months=[]; cur=start
    while cur<=end: months.append(cur); cur=shift_month(cur,1)
    return months

def render_students(operator):
    st.title("生徒管理")
    tab1,tab2=st.tabs(["生徒一覧・編集","新規登録"])
    with tab1:
        q=st.text_input("氏名検索"); known=sorted({s['school_location'] for s in list_students()}); school=st.selectbox("教室",[""]+known,format_func=lambda x:x or "すべて"); status=st.selectbox("在籍状況",["","在籍","休会","退会"],format_func=lambda x:x or "すべて")
        rows=list_students(q,school,status)
        for s in rows:
            sid=s['student_id']
            status_key=f'status_{sid}'; wd_key=f'wd_{sid}'; fbm_key=f'fbm_{sid}'
            fbm_auto_key=f'fbm_auto_{sid}'; fbm_manual_key=f'fbm_manual_{sid}'
            with st.expander(f"{s['name']}　{s['school_location']}　{s['enrollment_status']}"):
                # 在籍状況はst.formの外に置き、選択しただけで画面表示（退会日・最終請求月の表示切替）が
                # 即座に反映されるようにする。ここではまだDBへ保存しない（保存は下の保存ボタンのみ）。
                if status_key not in st.session_state: st.session_state[status_key]=s['enrollment_status']
                es=st.selectbox("在籍状況",["在籍","休会","退会"],key=status_key)

                withdrawal_date_val=None; final_billing_month_val=None
                if es=='退会':
                    if wd_key not in st.session_state:
                        if s['enrollment_status']=='退会' and s.get('withdrawal_date'):
                            st.session_state[wd_key]=date.fromisoformat(s['withdrawal_date'])
                        elif s['enrollment_status']=='退会':
                            st.session_state[wd_key]=None  # 既存が退会だが退会日未設定（要入力）
                        else:
                            st.session_state[wd_key]=date.today()  # 新しく退会へ切り替えた場合の初期値
                    withdrawal_date_val=st.date_input("退会日",key=wd_key)

                    wd_ym=withdrawal_date_val.strftime('%Y-%m') if withdrawal_date_val else None
                    if fbm_key not in st.session_state:
                        if s.get('final_billing_month'):
                            st.session_state[fbm_key]=s['final_billing_month']
                            st.session_state[fbm_auto_key]=s['final_billing_month']
                            st.session_state[fbm_manual_key]=True
                        else:
                            st.session_state[fbm_key]=wd_ym
                            st.session_state[fbm_auto_key]=wd_ym
                            st.session_state[fbm_manual_key]=False
                    else:
                        if st.session_state[fbm_key]!=st.session_state.get(fbm_auto_key):
                            st.session_state[fbm_manual_key]=True
                        if not st.session_state.get(fbm_manual_key) and wd_ym!=st.session_state.get(fbm_auto_key):
                            st.session_state[fbm_key]=wd_ym; st.session_state[fbm_auto_key]=wd_ym

                    fbm_choices=[None]+_final_billing_month_choices(withdrawal_date_val or date.today())
                    if st.session_state[fbm_key] and st.session_state[fbm_key] not in fbm_choices:
                        fbm_choices=[None]+sorted(set(fbm_choices[1:])|{st.session_state[fbm_key]})
                    final_billing_month_val=st.selectbox("レッスン料の最終請求月",fbm_choices,key=fbm_key,
                      format_func=lambda v:"選択してください" if v is None else month_label(v))
                    st.caption("初期値は退会日の年月です。退会日を変更すると、まだ手動変更していない間だけ連動します。")

                with st.form(f"edit{sid}"):
                    name=st.text_input("氏名",s['name']); locs=list(dict.fromkeys(SCHOOLS+[s['school_location']])); loc=st.selectbox("教室",locs,index=locs.index(s['school_location'])); grades=list(dict.fromkeys(GRADES+[s['grade']])); grade=st.selectbox("学年",grades,index=grades.index(s['grade']))
                    c=st.columns(2); mf=c[0].number_input("月謝",0,value=s['monthly_fee'],step=500); rf=c[1].number_input("発表会費",0,value=s['recital_fee'],step=500)
                    guardian=st.text_input("保護者名",s['guardian_name']); phone=st.text_input("電話",s['phone']); email=st.text_input("メール",s['email']); notes=st.text_area("備考",s['notes'])
                    if st.form_submit_button("変更を保存"):
                        if es=='退会' and (withdrawal_date_val is None or final_billing_month_val is None):
                            st.error("退会日とレッスン料の最終請求月の両方を入力してください。")
                        else:
                            save_student(dict(name=name,school_location=loc,grade=grade,monthly_fee=mf,recital_fee=rf,
                              enrollment_date=s['enrollment_date'],
                              withdrawal_date=withdrawal_date_val.isoformat() if es=='退会' else s.get('withdrawal_date'),
                              enrollment_status=es,
                              final_billing_month=final_billing_month_val if es=='退会' else s.get('final_billing_month'),
                              guardian_name=guardian,phone=phone,email=email,notes=notes),operator,sid)
                            for k in (status_key,wd_key,fbm_key,fbm_auto_key,fbm_manual_key): st.session_state.pop(k,None)
                            st.success("保存しました"); st.rerun()
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
    months=month_choices(); default_target=shift_month(date.today().strftime('%Y-%m'),1)
    target=st.selectbox("レッスン料の対象月",months,index=months.index(default_target),format_func=month_label)
    if st.session_state.get('_monthly_due_target')!=target:
        st.session_state['monthly_due']=previous_month_end(target); st.session_state['_monthly_due_target']=target
    due=st.date_input("支払期限",key='monthly_due')
    due_default=previous_month_end(target)
    st.caption(f"例：{int(target[:4])}年{int(target[5:7])}月分のレッスン料は、{due_default.year}年{due_default.month}月{due_default.day}日が支払期限です。")

    eligibility=monthly_billing_eligibility(target)

    unset=[e for e in eligibility if e['enrollment_status']=='退会' and not e.get('final_billing_month')]
    if unset:
        names='、'.join(e['name'] for e in unset)
        st.warning(f"レッスン料の最終請求月が未設定の退会者が{len(unset)}名います。（{names}）")

    st.subheader("請求対象チェックリスト")
    display_rows=[{
        '生徒名':e['name'],'教室':e['school_location'],'月謝額':e['monthly_fee'],
        '入会日':e.get('enrollment_date') or '',
        '退会日':e.get('withdrawal_date') or '',
        '最終請求月':e.get('final_billing_month') or '',
        '在籍状況':e['enrollment_status'],
        '対象判定':'対象' if e['eligible'] else '対象外',
        '対象外理由':e['reason'] if not e['eligible'] else '',
        '同月請求':'作成済み' if e['already_billed'] else '未作成',
    } for e in eligibility]
    st.dataframe(pd.DataFrame(display_rows),use_container_width=True,hide_index=True)

    actionable=[e for e in eligibility if e['eligible'] and not e['already_billed']]
    if actionable:
        st.caption("チェックを外すと、その生徒は今回の請求作成対象から除外されます。対象外の生徒はチェック欄がありません。")
    checked_ids=[]
    for e in actionable:
        key=f"monthly_check_{target}_{e['student_id']}"
        if key not in st.session_state: st.session_state[key]=True
        if st.checkbox(f"{e['name']}（{e['school_location']}・{money(e['monthly_fee'])}）",key=key):
            checked_ids.append(e['student_id'])

    checked_students=[e for e in actionable if e['student_id'] in checked_ids]
    st.info(f"対象 {len(checked_students)}人 / 請求予定合計 {money(sum(e['monthly_fee'] for e in checked_students))}")
    if st.checkbox("対象人数と金額を確認しました") and st.button(f"{int(target[5:])}月請求作成",type="primary",use_container_width=True):
        r=create_monthly(target,due.isoformat(),operator,student_ids=checked_ids); st.success(f"新規作成 {r['created']}件 / 重複スキップ {r['skipped']}件 / 請求総額 {money(r['total'])}")

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
