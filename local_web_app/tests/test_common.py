from datetime import date, datetime, timezone

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

def test_previous_month_end_normal_month():
    assert common.previous_month_end("2026-08") == date(2026, 7, 31)

def test_previous_month_end_year_boundary():
    assert common.previous_month_end("2026-01") == date(2025, 12, 31)

def test_previous_month_end_non_leap_february():
    assert common.previous_month_end("2027-03") == date(2027, 2, 28)

def test_previous_month_end_leap_year():
    assert common.previous_month_end("2028-03") == date(2028, 2, 29)

def test_next_jan31_from_within_january_is_same_year():
    assert common.next_jan31("2026-01-15") == date(2026, 1, 31)

def test_next_jan31_from_other_months_is_next_year():
    assert common.next_jan31("2026-07-23") == date(2027, 1, 31)
    assert common.next_jan31("2026-12-31") == date(2027, 1, 31)

def test_next_jan31_defaults_to_today_jst(monkeypatch):
    monkeypatch.setattr(common, "datetime", _FixedDatetime)
    assert common.next_jan31() == date(2027, 1, 31)

def test_shift_month_forward_within_year():
    assert common.shift_month("2026-07", 1) == "2026-08"
    assert common.shift_month("2026-07", 2) == "2026-09"

def test_shift_month_forward_across_year_boundary():
    assert common.shift_month("2026-12", 1) == "2027-01"

def test_shift_month_backward_across_year_boundary():
    assert common.shift_month("2026-01", -1) == "2025-12"

def test_shift_month_zero_is_identity():
    assert common.shift_month("2026-07", 0) == "2026-07"
