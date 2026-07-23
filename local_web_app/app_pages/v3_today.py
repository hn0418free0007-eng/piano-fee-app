from datetime import date
import streamlit as st
from services.auth_service import settings,current_user
from services.calendar_service import fetch_today_events,match_students
from services.calendar_mapping_service import get_mappings,save_mapping
from services.v3_repository import students,charges,complete
from services.sales_service import today_received_amount
from services.charge_service import monthly_payment_status

def yen(v): return f"{int(v):,}円"

def _due_label(due):
    if not due: return ''
    y,m,d=due.split('-')
    return f"{y}年{int(m)}月{int(d)}日"

def render_monthly_status(status):
    month=int(status['target_month'][5:7])
    if status['state']=='paid':
        st.success(f"✅ {month}月分まで支払済み")
    elif status['state']=='due_soon':
        st.info(f"🕒 {month}月分 未払い　支払期限：{_due_label(status['due_date'])}")
    elif status['state']=='due_today':
        st.warning(f"🟡 {month}月分 本日が支払期限です　支払期限：{_due_label(status['due_date'])}")
    elif status['state']=='overdue':
        st.error(f"⚠️ {month}月分が未入金です　支払期限：{_due_label(status['due_date'])}　期限超過 {status['overdue_days']}日")
    elif status['state']=='due_unset':
        st.warning(f"⚠️ {month}月分 未払い・支払期限が未設定です")
    elif status['state']=='missing':
        st.warning(f"⚠️ {month}月分の請求が未作成です")

def _charge_sort_key(c):
    """受領対象の並び順・初期選択: 月謝を優先し、月謝の中ではdue_dateが古い順
    （未設定は最後）、同一・未設定同士はtarget_monthが古い順。月謝以外は
    従来通りtarget_monthのみで並べる（受領処理・complete()自体は変更しない）。"""
    if c['charge_type']!='月謝': return (1,False,'',c['target_month'])
    return (0,not c.get('due_date'),c.get('due_date') or '',c['target_month'])

def load_today():
    s=settings(); user=current_user() or {}; token=user.get('provider_token')
    cal=s.get('google_calendar',{}); app=s.get('app',{})
    events=fetch_today_events(token,cal.get('calendar_id','primary'),app.get('timezone','Asia/Tokyo'))
    return match_students(events,students(),get_mappings()),not bool(token)

def render(operator):
    st.title("今日のレッスン")
    try: lessons,demo=load_today()
    except Exception as e:
        st.error(f"Googleカレンダーを取得できません: {e}"); lessons=match_students([],students()); demo=False
    if demo: st.info("デモモード：Google認証後は実際の今日の予定を表示します。")
    done=amount=recital=0; payable=0
    for lesson in lessons:
        student=lesson['student']
        if not student: continue
        cs=charges(student['student_id']); payable+=bool(cs)
        # 当月月謝を優先し、それ以外は期限・対象順
        cs=sorted(cs,key=lambda c:(c['charge_type']!='月謝',c['target_month']))
        if st.session_state.get(f"done_{lesson['event_id']}"): done+=1
    m=st.columns(4,gap="medium"); m[0].metric("今日のレッスン",f"{len(lessons)}名"); m[1].metric("今日の受領済",f"{done}名"); m[2].metric("未受領",f"{max(payable-done,0)}名"); m[3].metric("本日の受領額",yen(today_received_amount()))
    st.caption("本日、受領登録された金額の合計です。取消済みは含みません。")
    if not lessons:
        st.markdown('<div class="empty-state"><div class="icon">📅</div>'
          '<p class="title">今日のレッスン予定はありません</p>'
          '<p class="hint">Google Calendarに予定が登録されると、ここに表示されます。</p></div>',unsafe_allow_html=True)
        return
    for lesson in lessons:
        with st.container(border=True):
            st.markdown(f"## {lesson['time']}　{lesson['title']}")
            student=lesson['student']
            if not student:
                st.warning("未照合：自動登録しません。正しい生徒を確認して選択してください。")
                all_students=students(); lookup={s['student_id']:s for s in all_students}
                selected=st.selectbox("この予定を紐付ける生徒",[None]+list(lookup),key=f"map_{lesson['event_id']}",format_func=lambda x:"選択してください" if x is None else lookup[x]['name'])
                if selected and st.button("この紐付けを保存",key=f"save_map_{lesson['event_id']}",use_container_width=True):
                    save_mapping(lesson['normalized_title'],lesson['title'],selected,operator); st.success("保存しました。次回以降も利用します。"); st.rerun()
                continue
            st.caption(f"照合: {lesson['match_status']}")
            render_monthly_status(monthly_payment_status(student['student_id']))
            cs=sorted(charges(student['student_id']),key=_charge_sort_key)
            if not cs: st.success("未入金の請求はありません。"); continue
            choices={c['charge_id']:c for c in cs}
            if len(choices)==1:
                cid=next(iter(choices))
            else:
                def charge_label(x):
                    item=choices.get(x)
                    return "請求を再選択してください" if not item else f"{item['target_month']} {item['charge_type']}　{yen(item['charge_amount']-item.get('paid',0))}"
                cid=st.selectbox("今回受領する請求",list(choices),key=f"charge_{lesson['event_id']}",format_func=charge_label)
                if cid not in choices:
                    st.warning("請求を再選択してください。"); continue
            c=choices[cid]; st.markdown(f"### {c['target_month']} {c['charge_type']}　{yen(c['charge_amount']-c.get('paid',0))}")
            method=st.selectbox("支払方法",["現金","振込","口座振替","PayPay","その他"],key=f"method_{lesson['event_id']}")
            if st.session_state.get(f"done_{lesson['event_id']}"): st.success("✅ 受領・押印済み")
            elif st.button("受領・押印済み",key=f"complete_{lesson['event_id']}",type="primary",use_container_width=True):
                try:
                    pid=complete(c,student,method,operator,lesson['event_id']); st.session_state[f"done_{lesson['event_id']}"]=pid; st.rerun()
                except Exception as e: st.error(f"登録できませんでした: {e}")
