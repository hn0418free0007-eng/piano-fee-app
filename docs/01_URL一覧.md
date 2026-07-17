# URL一覧

## 目的

開発・運用で使うサービスの入口をまとめます。個別プロジェクトURLがリポジトリから確認できないものは、秘密情報や推測を書かず「未設定」としています。

最終更新日: 2026-07-17

## 一覧

| 項目 | 用途 | URL | ログイン方法 | Project名 | 備考 |
|---|---|---|---|---|---|
| GitHub | ソースコード管理サービス | https://github.com/ | GitHubアカウント | 未設定 | Repository一覧やアカウント設定を開く入口 |
| GitHub Repository | このプロジェクトのコード・履歴 | https://github.com/hn0418free0007-eng/piano-fee-app | GitHubアカウント | `piano-fee-app` | `main` が本番デプロイ対象ブランチ |
| Streamlit Community Cloud | アプリのデプロイ・ログ・Secrets管理 | https://share.streamlit.io/ | GitHub連携 | 未設定 | Main file pathは `local_web_app/app.py` |
| 本番アプリURL | 先生が日常利用するWebアプリ | 未設定 | Googleログイン | ピアノ教室運営 Ver.3 | Community CloudのApp URLを確認後に記入する |
| Supabase Dashboard | PostgreSQL、Auth、RLS、SQL Editor管理 | https://supabase.com/dashboard | 登録済みアカウント | 未設定 | 個別Project URLは記録せずDashboardから選択する |
| Google Cloud Console | OAuthクライアントとCalendar API管理 | https://console.cloud.google.com/ | Googleアカウント | 未設定 | OAuth Client Secretを文書へ書かない |
| Google Calendar | レッスン予定の入力・確認 | https://calendar.google.com/ | 先生用Googleアカウント | `primary` | 予定タイトルを生徒名に合わせる |
| ChatGPT | 調査、設計、開発支援 | https://chatgpt.com/ | 利用中のアカウント | piano-fee-app | 新規チャットでは `docs/08_CHATGPT引継ぎ.md` を渡す |
| Claude | コード調査・開発支援 | https://claude.ai/ | 利用中のアカウント | piano-fee-app | Repositoryを開いたうえで引継ぎ資料を読ませる |
| Gemini | Google関連の調査・開発支援 | https://gemini.google.com/ | Googleアカウント | piano-fee-app | Secretや実データを入力しない |

## 更新方法

本番URLやProject名が確定したら、このファイルの「未設定」だけを更新します。APIキー、メールアドレス、Project Secret、Database Passwordは記載しません。
