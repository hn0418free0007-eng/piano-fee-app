from app_pages.v3_today import _charge_sort_key

def _c(target_month,charge_type,due_date=None):
    return {'target_month':target_month,'charge_type':charge_type,'due_date':due_date}

def test_oldest_due_date_comes_first():
    rows=[_c('2026-09','月謝','2026-08-31'),_c('2026-08','月謝','2026-07-31')]
    ordered=sorted(rows,key=_charge_sort_key)
    assert [r['target_month'] for r in ordered]==['2026-08','2026-09']

def test_due_unset_comes_after_due_dated():
    rows=[_c('2026-07','月謝',None),_c('2026-09','月謝','2026-08-31')]
    ordered=sorted(rows,key=_charge_sort_key)
    assert [r['target_month'] for r in ordered]==['2026-09','2026-07']

def test_same_or_unset_due_date_falls_back_to_target_month():
    rows=[_c('2026-09','月謝',None),_c('2026-08','月謝',None)]
    ordered=sorted(rows,key=_charge_sort_key)
    assert [r['target_month'] for r in ordered]==['2026-08','2026-09']

def test_monthly_fee_always_precedes_other_charge_types():
    rows=[_c('2026-01','発表会費','2020-01-01'),_c('2026-12','月謝',None)]
    ordered=sorted(rows,key=_charge_sort_key)
    assert ordered[0]['charge_type']=='月謝'
    assert ordered[1]['charge_type']=='発表会費'
