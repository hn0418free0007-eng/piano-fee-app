from datetime import date
import pandas as pd
import streamlit as st
from services.sales_service import monthly_sales,yearly_sales,student_yearly_sales,recital_sales
from services.export_service import to_csv,to_excel

def month_options():
    y=date.today().year
    return [f"{yy}-{m:02d}" for yy in range(y-2,y+2) for m in range(1,13)]
def dl(rows,name):
    a,b=st.columns(2); a.download_button("CSV出力",to_csv(rows),f"{name}.csv",use_container_width=True); b.download_button("Excel出力",to_excel(rows,name),f"{name}.xlsx",use_container_width=True)
def show(rows,name):
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True); st.metric("合計",f"{sum(r['売上金額'] for r in rows):,}円"); dl(rows,name)
def render():
    st.title("売上管理・確定申告")
    tab1,tab2,tab3,tab4=st.tabs(["月別売上","年間売上","生徒別年間","発表会費"])
    with tab1:
        opts=month_options(); default=opts.index(date.today().strftime('%Y-%m')); ym=st.selectbox("対象年月",opts,index=default); show(monthly_sales(ym),f"月別売上_{ym}")
    with tab2:
        year=st.selectbox("対象年",list(range(date.today().year-5,date.today().year+2)),index=5); show(yearly_sales(year),f"年間売上_{year}")
    with tab3:
        year2=st.selectbox("対象年",list(range(date.today().year-5,date.today().year+2)),index=5,key='student_year'); show(student_yearly_sales(year2),f"生徒別年間売上_{year2}")
    with tab4:
        event=st.selectbox("年度・開催",["",str(date.today().year),str(date.today().year-1)],format_func=lambda x:x or "すべて"); show(recital_sales(event),f"発表会費売上_{event or '全期間'}")

