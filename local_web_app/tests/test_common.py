from datetime import datetime, timezone

import services.common as common


class _FixedDatetime(datetime):
    """テスト実行環境のタイムゾーンに関係なく、固定のUTC時刻を返すdatetime差し替え用。"""
    @classmethod
    def now(cls, tz=None):
        fixed_utc = datetime(2026, 7, 23, 23, 30, tzinfo=timezone.utc)
        return fixed_utc.astimezone(tz) if tz else fixed_utc

def test_today_jst_resolves_by_asia_tokyo_offset_not_system_clock(monkeypatch):
    """
    UTC 2026-07-23 23:30は、Asia/Tokyo（UTC+9）では既に2026-07-24 08:30。
    date.today()やDBサーバーのcurrent_dateのような、実行環境のタイムゾーンに
    依存した日付ではなく、Asia/Tokyoへ変換した日付が返ることを確認する。
    """
    monkeypatch.setattr(common, "datetime", _FixedDatetime)
    assert common.today_jst() == "2026-07-24"
