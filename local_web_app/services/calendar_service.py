from __future__ import annotations
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import requests
import re

def mock_events(day=None):
    day=day or date.today(); names=['さくら みらい','あおぞら かなで','未登録 サンプル']
    return [{'event_id':f'mock-{i}','start':datetime.combine(day,time(16+i,30),ZoneInfo('Asia/Tokyo')),
      'time':f'{16+i}:30','title':name} for i,name in enumerate(names)]

def fetch_today_events(provider_token=None,calendar_id='primary',timezone='Asia/Tokyo',day=None,requester=requests):
    if not provider_token: return mock_events(day)
    tz=ZoneInfo(timezone); day=day or datetime.now(tz).date()
    start=datetime.combine(day,time.min,tz); end=start+timedelta(days=1)
    url=f"https://www.googleapis.com/calendar/v3/calendars/{requests.utils.quote(calendar_id,safe='')}/events"
    params={'timeMin':start.isoformat(),'timeMax':end.isoformat(),'singleEvents':'true','orderBy':'startTime','timeZone':timezone}
    res=requester.get(url,headers={'Authorization':f'Bearer {provider_token}'},params=params,timeout=15); res.raise_for_status()
    result=[]
    for item in res.json().get('items',[]):
        raw=item.get('start',{}).get('dateTime')
        if not raw: continue
        dt=datetime.fromisoformat(raw.replace('Z','+00:00')).astimezone(tz)
        result.append({'event_id':item['id'],'start':dt,'time':dt.strftime('%H:%M'),'title':item.get('summary','（タイトルなし）').strip()})
    return sorted(result,key=lambda x:x['start'])

def normalize_title(value):
    value=re.sub(r'[\s\u3000]+',' ',str(value or '')).strip()
    return re.sub(r'\s+(レッスン|lesson)$','',value,flags=re.IGNORECASE).strip()

def match_students(events,students,mappings=None):
    mappings=mappings or {}
    buckets={}
    for s in students: buckets.setdefault(normalize_title(s['name']),[]).append(s)
    by_id={s['student_id']:s for s in students}
    result=[]
    for event in events:
        key=normalize_title(event['title']); candidates=buckets.get(key,[]); student=None; status='未照合'
        if len(candidates)==1: student=candidates[0]; status='自動照合'
        elif key in mappings and mappings[key] in by_id: student=by_id[mappings[key]]; status='手動照合'
        # 正規化後に同名候補が複数なら、保存済み対応がない限り自動決定しない。
        result.append({**event,'normalized_title':key,'student':student,'match_status':status})
    return result

