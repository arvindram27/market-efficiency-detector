"""Synthetic data only. No imports of the real Apple adapter or fixture."""
from dataclasses import replace
from datetime import timedelta
from tests_timing.test_mt1 import spec,fixture,bar,T,STEP

def scenarios():
    s=spec();base=fixture(s)
    delayed=spec(receipt=T+timedelta(seconds=2))
    delayed_bars=fixture(delayed,True)
    delayed_bars=[replace(b,available_ts=T+92*STEP) if b.open_ts==T+79*STEP else b for b in delayed_bars]
    unknown=list(delayed_bars);unknown[0]=replace(unknown[0],available_ts=None)
    shifted=spec(publication=T+timedelta(seconds=30))
    none=[bar(b.open_ts,99 if i%2 else 101) if b.open_ts>=T else b for i,b in enumerate(base)]
    big=[bar(b.open_ts,b.close*1e90) for b in base]
    bad=list(base);bad[0]=replace(bad[0],low=200)
    off=list(base);off[0]=replace(off[0],open_ts=off[0].open_ts+timedelta(seconds=1))
    return [
        ('gate-negative-stable',s,base),('negative-no-streak',s,none),
        ('delayed-arrival',delayed,delayed_bars),('one-unknown-arrival',delayed,unknown),
        ('unknown-receipt',s,fixture(s,True)),('straddling',shifted,fixture(shifted)+[bar(T,100)]),
        ('missing-pre',s,base[1:]),('missing-observation',s,[b for b in base if b.open_ts!=T+20*STEP]),
        ('missing-reference',s,[b for b in base if b.open_ts!=T+80*STEP]),
        ('zero-scale',s,[bar(b.open_ts,100) for b in base]),('reversed',s,list(reversed(base))),
        ('huge-finite',s,big),('duplicate',s,base+[base[0]]),('bad-ohlc',s,bad),('offgrid',s,off),
        ('bad-spec',replace(s,interval_seconds=True),base),
        ('naive-spec',replace(s,publication=T.replace(tzinfo=None)),base),
        ('unavailable-early',s,[replace(b,available_ts=b.open_ts) for b in base]),
        ('extra-after-horizon',s,base+[bar(T+90*STEP,10000)])]
