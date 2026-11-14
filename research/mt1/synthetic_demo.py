"""Deterministic made-up examples. No files, network, Spark or work on import.
Run from this directory: python -B synthetic_demo.py
"""
import json
import math
from datetime import datetime,timedelta,timezone
from med_timing import Bar,Study,evaluate

PUBLICATION=datetime(2026,1,12,14,tzinfo=timezone.utc)
STEP=timedelta(minutes=1)

def study(case):
    return Study(publication=PUBLICATION,headline='Central bank monetary policy announcement',
        ticker='SYNTH',study_id='synthetic-'+case,source_url='https://example.invalid/synthetic',
        data_vintage='deterministic-made-up-candles',input_sha256='0'*64)

def candle(at,close):return Bar(at,close,close,close,close,1.0,None)

def make_case(case):
    """60 complete pre candles and90complete observation candles, no arrivals.
    Prices are illustrative paths, not fitted to any real event or result.
    """
    if case not in ('stable','no_streak','missing_reference'):raise ValueError('unknown synthetic case')
    value=100.0;bars=[]
    for i in range(60):
        if i:value*=math.exp(0.01 if i%2 else -0.01)
        bars.append(candle(PUBLICATION+(i-60)*STEP,value))
    for i in range(90):
        close=(99.0 if i%2 else 101.0) if case=='no_streak' else 100.0
        if case=='missing_reference' and i==80:continue
        bars.append(candle(PUBLICATION+i*STEP,close))
    return study(case),bars

def main():
    records=[]
    for name in ('stable','no_streak','missing_reference'):
        s,bars=make_case(name);result=evaluate(s,bars)
        records.append({'case':name,'scope':'synthetic retrospective example, not real-market evidence',
            'gate_status':result['gate_status'],'gate_reason':result['gate_reason'],
            'reference_status':result['reference_status'],'coverage_status':result['coverage_status'],
            'stabilization_status':result['stabilization_status'],
            'candidate_close_delay_seconds':result['candidate_close_delay_seconds'],
            'confirmation_close_delay_seconds':result['confirmation_close_delay_seconds'],
            'result_available_lower_bound_ts':result['result_available_lower_bound_ts'],
            'result_available_ts':result['result_available_ts'],
            'result_information_status':result['result_information_status']})
    print(json.dumps(records,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
