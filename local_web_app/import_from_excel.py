"""既存Excelをプレビューし、明示確認後に生徒マスタを取り込むツール。元ファイルは変更しない。"""
from pathlib import Path
import argparse
import pandas as pd
from database import init_db
from services.student_service import save_student

ALIASES={
 'name':['氏名','生徒名','名前'], 'school_location':['教室','教室名'], 'grade':['学年'],
 'monthly_fee':['月謝','月謝額','レッスン料'], 'recital_fee':['発表会費'],
 'guardian_name':['保護者名'], 'phone':['電話','電話番号'], 'email':['メール','メールアドレス'],
 'notes':['備考'], 'enrollment_status':['在籍状況','状態']
}

def read_preview(path):
    book=pd.ExcelFile(path); sheet='生徒マスタ' if '生徒マスタ' in book.sheet_names else book.sheet_names[0]
    raw=pd.read_excel(path,sheet_name=sheet)
    mapped={}
    for target,names in ALIASES.items():
        for name in names:
            if name in raw.columns: mapped[target]=name; break
    if 'name' not in mapped: raise ValueError("氏名または生徒名の列を特定できませんでした。")
    out=pd.DataFrame({k:raw[v] for k,v in mapped.items()}).dropna(subset=['name'])
    return sheet,out

def import_rows(frame,operator):
    init_db(seed=False); count=0
    for _,r in frame.iterrows():
        def val(k,default=''):
            v=r.get(k,default); return default if pd.isna(v) else v
        save_student(dict(name=str(val('name')),school_location=str(val('school_location','未設定')),grade=str(val('grade')),
          monthly_fee=int(val('monthly_fee',0)),recital_fee=int(val('recital_fee',0)),enrollment_date=None,withdrawal_date=None,
          enrollment_status=str(val('enrollment_status','在籍')) if str(val('enrollment_status','在籍')) in ['在籍','休会','退会'] else '在籍',
          guardian_name=str(val('guardian_name')),phone=str(val('phone')),email=str(val('email')),notes=str(val('notes'))),operator)
        count+=1
    return count

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('excel',nargs='?',default='../ピアノ教室_レッスン料管理.xlsx'); ap.add_argument('--commit',action='store_true'); args=ap.parse_args()
    path=Path(args.excel); sheet,frame=read_preview(path)
    print(f"元ファイル: {path.resolve()} / シート: {sheet} / 候補: {len(frame)}件")
    print(frame.head(20).to_string(index=False))
    if not args.commit:
        print("プレビューのみです。確認後、--commit を付けて再実行してください。"); return
    answer=input("上記を新DBへ登録します。IMPORT と入力してください: ")
    if answer!='IMPORT': print("中止しました。"); return
    print(f"{import_rows(frame,'Excel移行')}件を登録しました。元Excelは変更していません。")
if __name__=='__main__': main()

