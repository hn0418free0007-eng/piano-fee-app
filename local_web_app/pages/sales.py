from datetime import date
import pandas as pd
import streamlit as st
from services.sales_service import (monthly_billed_amount,monthly_received_amount,
  yearly_billed_amount,yearly_received_amount,
  student_yearly_billed_amount,student_yearly_received_amount,recital_billed_amount)
from services.export_service import to_csv,to_excel

BASIS_OPTIONS=["請求月別の金額","受領月別の金額"]
BASIS_HELP="請求月別＝何月分の請求に対する入金かで集計します。受領月別＝実際に何月に受領したかで集計します。前受金・後払いがあると、両者の金額は一致しません。"

def month_options():
    y=date.today().year
    return [f"{yy}-{m:02d}" for yy in range(y-2,y+2) for m in range(1,13)]
def dl(rows,name):
    a,b=st.columns(2); a.download_button("CSV出力",to_csv(rows),f"{name}.csv",use_container_width=True); b.download_button("Excel出力",to_excel(rows,name),f"{name}.xlsx",use_container_width=True)
def show(rows,name):
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); st.metric("合計",f"{sum(r['金額'] for r in rows):,}円"); dl(rows,name)
def render():
    st.title("売上管理・確定申告")
    tab1,tab2,tab3,tab4=st.tabs(["月別集計","年間集計","生徒別年間集計","発表会費"])
    with tab1:
        opts=month_options(); default=opts.index(date.today().strftime('%Y-%m')); ym=st.selectbox("対象年月",opts,index=default)
        basis=st.radio("集計基準",BASIS_OPTIONS,horizontal=True,key='sales_monthly_basis',help=BASIS_HELP)
        if basis=="請求月別の金額":
            st.caption(f"{ym} 分として請求された入金の合計です（受領日は問いません）。")
            show(monthly_billed_amount(ym),f"請求月別_{ym}")
        else:
            st.caption(f"{ym} 中に実際に受領した入金の合計です（前受金・後払いを含みます）。")
            show(monthly_received_amount(ym),f"受領月別_{ym}")
    with tab2:
        year=st.selectbox("対象年",list(range(date.today().year-5,date.today().year+2)),index=5)
        basis2=st.radio("集計基準",BASIS_OPTIONS,horizontal=True,key='sales_yearly_basis',help=BASIS_HELP)
        if basis2=="請求月別の金額": show(yearly_billed_amount(year),f"請求年別_{year}")
        else: show(yearly_received_amount(year),f"受領年別_{year}")
    with tab3:
        year2=st.selectbox("対象年",list(range(date.today().year-5,date.today().year+2)),index=5,key='student_year')
        basis3=st.radio("集計基準",BASIS_OPTIONS,horizontal=True,key='sales_student_yearly_basis',help=BASIS_HELP)
        if basis3=="請求月別の金額": show(student_yearly_billed_amount(year2),f"生徒別請求年別_{year2}")
        else: show(student_yearly_received_amount(year2),f"生徒別受領年別_{year2}")
    with tab4:
        st.caption("発表会費は開催（請求対象月）を基準に集計します。")
        event=st.selectbox("年度・開催",["",str(date.today().year),str(date.today().year-1)],format_func=lambda x:x or "すべて")
        show(recital_billed_amount(event),f"発表会費売上_{event or '全期間'}")
