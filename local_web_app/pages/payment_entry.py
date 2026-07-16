from datetime import date
import streamlit as st
from services.student_service import list_students
from services.charge_service import open_charges
from services.payment_service import register_payment, confirm_stamp, pending_stamps

def money(v): return f"{int(v):,}円"

def render(operator):
    st.title("入金受付")
    schools=sorted({s['school_location'] for s in list_students(status='在籍')}); school=st.selectbox("教室で絞り込み",[""]+schools,format_func=lambda x:x or "すべて")
    search=st.text_input("生徒名を検索")
    students=list_students(search,school,"在籍")
    if not students: st.info("該当する在籍生徒はいません。"); return
    labels={s['student_id']:f"{s['name']}（{s['school_location']}）" for s in students}
    sid=st.selectbox("生徒を選択",labels,format_func=lambda x:labels[x])
    charges=open_charges(sid)
    if not charges: st.success("この生徒に未入金の請求はありません。"); return
    cmap={c['charge_id']:c for c in charges}
    cid=st.selectbox("対象請求",cmap,format_func=lambda x:f"{cmap[x]['target_month']} {cmap[x]['charge_type']} {money(cmap[x]['charge_amount'])}")
    c=cmap[cid]; remaining=c['charge_amount']-c['paid']
    st.markdown(f"### {c['name']} さん　{c['target_month']} {c['charge_type']}")
    x=st.columns(3); x[0].metric("請求額",money(c['charge_amount'])); x[1].metric("受領済額",money(c['paid'])); x[2].metric("残額",money(remaining))
    with st.form("payment_form"):
        amount=st.number_input("今回受取額",min_value=1,value=max(1,int(remaining)),step=100)
        received=st.date_input("受取日",date.today()); method=st.selectbox("支払方法",["現金","振込","口座振替","PayPay","その他"])
        notes=st.text_area("備考"); extra=st.checkbox("分割払い・追加徴収として残額超過を許可")
        submitted=st.form_submit_button("登録内容を確認する",type="primary",use_container_width=True)
    if submitted: st.session_state.payment_confirm=dict(cid=cid,amount=amount,date=received.isoformat(),method=method,notes=notes,extra=extra,name=c['name'],label=f"{c['target_month']} {c['charge_type']}")
    data=st.session_state.get('payment_confirm')
    if data and data['cid']==cid:
        st.warning(f"{data['name']}さん / {data['label']} / {money(data['amount'])}\n\nこの内容で受領登録しますか？")
        if st.button("はい、受領登録する",type="primary",use_container_width=True):
            try:
                pid=register_payment(data['cid'],data['amount'],data['date'],data['method'],operator,data['notes'],data['extra'])
                st.session_state.last_payment=pid; del st.session_state.payment_confirm
                st.success("受領登録が完了しました。\n\n次に、封筒へ受領印を押してください。")
            except ValueError as e: st.error(str(e))
    if st.session_state.get('last_payment'):
        if st.button("印鑑を押しました",type="primary",use_container_width=True):
            try: confirm_stamp(st.session_state.last_payment,operator); del st.session_state.last_payment; st.success("処理完了しました。")
            except ValueError as e: st.error(str(e))

def render_stamp(operator):
    st.title("印鑑未確認")
    rows=pending_stamps()
    if not rows: st.success("印鑑未確認の封筒はありません。"); return
    for r in rows:
        cols=st.columns([2,2,2,1,2,2]); cols[0].write(f"{r['received_date']} {r['received_time']}"); cols[1].write(r['student_name']); cols[2].write(f"{r['target_month']} {r['payment_type']}"); cols[3].write(money(r['amount_received'])); cols[4].write(r['received_by'])
        if cols[5].button("印鑑を押しました",key=f"stamp{r['payment_id']}",type="primary"): confirm_stamp(r['payment_id'],operator); st.rerun()

