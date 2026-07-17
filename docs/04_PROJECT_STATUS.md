# PROJECT STATUS

## 基本情報

- 基準日: 2026-07-17
- Repository: `piano-fee-app`
- 本番ブランチ: `main`
- アプリ起動ファイル: `local_web_app/app.py`
- システム名: ピアノ教室運営アプリ Ver.3

## 完成済み

- [x] GitHub連携
- [x] Streamlit Community Cloud公開
- [x] SQLiteからSupabaseへの移行機能
- [x] Supabase Google OAuth
- [x] Google Calendar API読取
- [x] 今日の受付
- [x] Calendar予定と生徒の自動照合
- [x] 手動照合結果の保存
- [x] 受領・押印済み登録
- [x] PostgreSQL RPCによる受領トランザクション
- [x] Identity Sequence同期実装
- [x] Streamlit外部リダイレクト対応PKCE修正
- [x] Row Level Securityと許可メールの二重制限
- [x] ローカルデモモードと自動テスト

## 現在の課題

- [ ] 本番データで売上画面を確認する
- [ ] 本番データで取消処理を確認する
- [ ] CSV出力内容と文字化けを確認する
- [ ] Excel出力内容と書式を確認する
- [ ] 既存SupabaseでIdentity Sequence同期SQLを実行・確認する
- [ ] Google provider token期限後の再ログイン運用を確認する

## 次回予定

1. 本番生徒・請求データを登録する
2. Identity Sequenceを同期する
3. 受領・取消・売上の一連運用をテストする
4. CSV・Excelを実データ相当で確認する
5. スマートフォンUIを改善する
6. 運用テスト結果をこの文書へ追記する

## 直近の重要変更

| 日付 | 内容 | 状態 | 関連ファイル |
|---|---|---|---|
| 2026-07-17 | PKCE verifierを外部リダイレクト越しに保持 | 完了 | `services/auth_service.py` |
| 2026-07-17 | Identity列の最大IDとシーケンスを同期 | 実装・本番実行待ち | `migrate_to_supabase.py`, `supabase_sequence_sync.sql` |
| 2026-07-17 | プロジェクト引継ぎ文書を整備 | 完了 | `docs/` |

## 更新履歴テンプレート

新しい記録は表の先頭へ追加します。

| 日付 | 担当 | 変更内容 | テスト結果 | コミットID | 本番確認 |
|---|---|---|---|---|---|
| YYYY-MM-DD | 名前またはAI | 内容 | `pytest: N passed` | `abcdef0` | 未確認／確認済み |

## 開発再開時チェック

```powershell
git status
git log -5 --oneline
cd local_web_app
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

未コミット差分がある場合は、所有者と目的を確認してから編集します。
