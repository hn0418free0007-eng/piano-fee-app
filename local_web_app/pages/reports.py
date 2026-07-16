import streamlit as st
import pandas as pd
from datetime import date
from services.charge_service import unpaid
from services.payment_service import history,cancel_payment
from services.dashboard_service import today_summary
from services.export_service import to_csv,to_excel,dataset
from services.backup_service import create_backup

def month_options():
    y=date.today().year
    return [""]+[f"{yy}-{m:02d}" for yy in range(y-2,y+2) for m in range(1,13)]
def month_label(v):
    if not v: return "すべて"
    y,m=v.split('-'); return f"{y}年{int(m)}月"

def downloads(rows,prefix):
    c=st.columns(2); c[0].download_button("CSVを保存",to_csv(rows),f"{prefix}.csv","text/csv",use_container_width=True); c[1].download_button("Excelを保存",to_excel(rows,prefix),f"{prefix}.xlsx",use_container_width=True)

def render_unpaid():
    st.title("未入金一覧")
    schools=sorted({r['school_location'] for r in unpaid()}); c=st.columns(5); month=c[0].selectbox("対象年月",month_options(),format_func=month_label); school=c[1].selectbox("教室",[""]+schools,format_func=lambda x:x or "すべて"); typ=c[2].selectbox("請求種別",["","月謝","発表会費","教材費","その他"],format_func=lambda x:x or "すべて"); status=c[3].selectbox("在籍状況",["","在籍","休会","退会"],format_func=lambda x:x or "すべて"); state=c[4].selectbox("状態",["","未入金","一部入金","期限超過"],format_func=lambda x:x or "すべて")
    rows=unpaid(dict(target_month=month,school=school,charge_type=typ,enrollment_status=status,state=state)); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); downloads(rows,"未入金一覧")

def render_history(operator):
    st.title("入金履歴")
    c=st.columns(3); name=c[0].text_input("生徒名検索"); month=c[1].selectbox("対象年月",month_options(),format_func=month_label,key='history_month'); received=c[2].date_input("受取日",value=None)
    c=st.columns(3); method=c[0].selectbox("支払方法",["","現金","振込","口座振替","PayPay","その他"],format_func=lambda x:x or "すべて"); who=c[1].selectbox("担当者",["","先生","受付担当","代講講師"],format_func=lambda x:x or "すべて"); typ=c[2].selectbox("請求種別",["","月謝","発表会費","教材費","その他"],format_func=lambda x:x or "すべて")
    rows=history(dict(name=name,target_month=month,received_date=received.isoformat() if received else '',method=method,operator=who,charge_type=typ)); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); downloads(rows,"入金履歴")
    with st.expander("入金を取消する（記録は残ります）"):
        ids=[r['payment_id'] for r in rows if not r['cancelled_at']]; pid=st.selectbox("入金ID",ids) if ids else None; reason=st.text_input("取消理由"); confirm=st.checkbox("取消内容を確認しました")
        if pid and confirm and st.button("この入金を取消する",type="primary"):
            try: cancel_payment(pid,reason,operator); st.success("取消しました"); st.rerun()
            except ValueError as e: st.error(str(e))

def render_daily():
    st.title("本日の受付一覧")
    rows=today_summary(); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    pending=sum(not r['stamp_confirmed'] for r in rows); st.write(f"受領 {len(rows)}件 / 合計 {sum(r['amount_received'] for r in rows):,}円 / 印鑑未確認 {pending}件")
    (st.warning if pending else st.success)("本日の処理はまだ完了していません。" if pending else "本日の受領処理はすべて完了しています。")

def render_exports(operator):
    st.title("データ出力・バックアップ")
    kind=st.selectbox("出力データ",["生徒一覧","入金履歴","月別売上一覧","年間売上一覧","操作履歴"]); rows=dataset(kind); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); downloads(rows,kind)
    st.divider()
    if st.button("今すぐデータベースをバックアップ",type="primary"):
        try: st.success(f"バックアップしました: {create_backup(operator).name}")
        except Exception as e: st.error(f"バックアップに失敗しました: {e}")
