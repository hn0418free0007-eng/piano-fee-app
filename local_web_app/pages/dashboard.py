import streamlit as st
from services.dashboard_service import metrics, today_summary

def money(v): return f"{int(v):,}円"

def render(go):
    st.title("ピアノ教室 受付ダッシュボード")
    cols=st.columns(5)
    for col,label,page in zip(cols,["入金を登録する","印鑑未確認を処理する","未入金一覧を見る","生徒を管理する","月次請求を作成する"],
                              ["入金受付","印鑑未確認","未入金一覧","生徒管理","月次請求作成"]):
        if col.button(label,use_container_width=True,type="primary"): go(page)
    m=metrics(); st.subheader("今月の状況")
    a=st.columns(5); a[0].metric("請求総額",money(m['charged'])); a[1].metric("入金総額",money(m['paid'])); a[2].metric("未入金額",money(m['unpaid'])); a[3].metric("未入金人数",f"{m['unpaid_people']}人"); a[4].metric("一部入金人数",f"{m['partial']}人")
    b=st.columns(4); b[0].metric("印鑑未確認",f"{m['pending_stamps']}人"); b[1].metric("本日の受領件数",f"{m['today_count']}件"); b[2].metric("本日の受領額",money(m['today_amount'])); b[3].metric("今月の発表会費未納",f"{m['recital_unpaid']}人")
    if m['pending_stamps']: st.error(f"印鑑未確認が {m['pending_stamps']}人あります。封筒へ受領印を押してください。")
    if st.button("本日の処理を確認する",use_container_width=True):
        rows=today_summary(); pending=[r for r in rows if not r['stamp_confirmed']]
        st.write(f"本日受領：{len(rows)}件 / 印鑑未確認：{len(pending)}件 / 受取額：{money(sum(r['amount_received'] for r in rows))}")
        st.write("生徒："+ ("、".join(r['student_name'] for r in rows) if rows else "なし"))
        (st.warning if pending else st.success)("本日の処理はまだ完了していません。" if pending else "本日の受領処理はすべて完了しています。")

