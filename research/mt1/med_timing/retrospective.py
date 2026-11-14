"""mt1 fixed-window retrospective study. No files, network, Spark or legacy imports."""
import math
from statistics import stdev, median
from datetime import timedelta, timezone
from .contracts import RESULT_FIELDS
from .validation import validate_spec, validate_bars, envelope, grids, iso, error

# Exact keyword order/substring semantics from the reviewed legacy contextualist.
KEYWORDS = (
 ('EARNINGS',('earnings','profit','revenue','quarter','q1','q2','q3','q4','results','guidance','net profit','eps','outlook','beat','miss')),
 ('MACRO',('rbi','fed','interest rate','rate hike','rate cut','inflation','gdp','cpi','policy','budget','fiscal','monetary','reserve bank')),
 ('M&A',('acquisition','acquires','acquire','merger','merges','takeover','buyout','stake','deal','combine','combines')))

def classify(headline):
    kind=next((k for k,words in KEYWORDS if any(w in headline.lower() for w in words)),'OTHER')
    weight='LOW' if kind=='OTHER' or len(headline.strip().split())<3 else 'HIGH'
    return kind,weight

def gate(z,kind,weight,threshold):
    if weight!='HIGH':return 'NOT_TRIGGERED','LOW_CONF','NONE'
    if kind not in ('EARNINGS','MACRO','M&A'):return 'NOT_TRIGGERED','EVENT_TYPE','NONE'
    if abs(z)<=threshold:return 'NOT_TRIGGERED','NO_PRICE_MOVE','NONE'
    return 'TRIGGERED',None,'LONG' if z>0 else 'SHORT'

def first_streak(opens, by_time, reference, sigma, mult, count):
    band=mult*sigma*reference; run=[]
    for t in opens:
        if abs(by_time[t].close-reference)<=band:
            run.append(t)
            if len(run)==count:return run[0],run[-1]
        else:run=[]
    return None,None

def evaluate(study,bars):
    errors=validate_spec(study)
    if errors:return envelope(errors)
    errors=validate_bars(bars,study)
    if errors:return envelope(errors)
    s=study;t=s.publication.astimezone(timezone.utc);step=timedelta(seconds=s.interval_seconds)
    gs=grids(s);by={b.open_ts.astimezone(timezone.utc):b for b in bars}
    missing={role:[x for x in opens if x not in by] for role,opens in gs.items()}
    complete=not any(missing.values())
    sigma=None
    if not missing['PRE']:
        closes=[by[x].close for x in gs['PRE']]
        returns=[(math.log(b)-math.log(a)) for a,b in zip(closes,closes[1:])]
        sigma=stdev(returns)
    z=None;kind,weight=classify(s.headline)
    if missing['PRE'] or missing['MOVE']:g,reason,direction='UNAVAILABLE_COVERAGE',None,'NONE'
    elif sigma is None or sigma<=0:g,reason,direction='UNAVAILABLE_SCALE',None,'NONE'
    else:
        ref=by[gs['PRE'][-1]].close
        zs=[(math.log(by[x].close)-math.log(ref))/(sigma*math.sqrt(k)) for k,x in enumerate(gs['MOVE'],1)]
        z=max(zs,key=abs)
        g,reason,direction=gate(z,kind,weight,s.z_threshold)
    # Stable even-count median avoids overflow from adding two large prices.
    ref_closes=sorted(by[x].close for x in gs['REFERENCE'] if x in by)
    n=len(ref_closes)
    reference=None if missing['REFERENCE'] else (ref_closes[n//2] if n%2 else ref_closes[n//2-1]/2+ref_closes[n//2]/2)
    if reference is not None and sigma is not None and sigma>0 and (not math.isfinite(s.band_sigma_mult*sigma*reference) or s.band_sigma_mult*sigma*reference<=0):
        return envelope([error('NONFINITE_VALUE','derived_stability_band')])
    ref_status='AVAILABLE' if reference is not None else 'UNAVAILABLE_COVERAGE'
    first=last=None
    if reference is None:stability='UNAVAILABLE_REFERENCE'
    elif sigma is None or sigma<=0:stability='UNAVAILABLE_PRE_SCALE'
    elif missing['OBSERVATION']:stability='INSUFFICIENT_OBSERVATION_COVERAGE'
    else:
        first,last=first_streak(gs['OBSERVATION'],by,reference,sigma,s.band_sigma_mult,s.consecutive_bars)
        stability='CONFIRMED' if first is not None else 'NOT_STABILIZED_BY_HORIZON'
    required=sorted(set(x for opens in gs.values() for x in opens))
    lower=max([t]+[x+step for x in required]) if complete else None
    available=None
    if complete and s.receipt is not None and all(by[x].available_ts is not None for x in required):
        available=max([s.receipt]+[by[x].available_ts for x in required])
    excluded=[]
    floor=t.replace(second=0,microsecond=0)
    if floor<t<floor+step:
        excluded=[{'bar_open_ts':iso(floor),'bar_close_ts':iso(floor+step),
                   'lost_pre_seconds':(t-floor).total_seconds(),'lost_post_seconds':(floor+step-t).total_seconds()}]
    record={
      'schema_version':'mt1.study_result','study_id':s.study_id,'ticker':s.ticker,'source_url':s.source_url,
      'exact_headline':s.headline,'data_vintage':s.data_vintage,'input_sha256':s.input_sha256,
      'algorithm_version':'mt1-python-prototype-1','source_revision':s.source_revision,
      'parameters':{'interval_seconds':s.interval_seconds,'pre_bars':s.pre_bars,'move_seconds':s.move_seconds,
        'observation_seconds':s.observation_seconds,'reference_start_offset_seconds':s.reference_start_seconds,
        'reference_end_offset_seconds':s.reference_end_seconds,'z_threshold':s.z_threshold,
        'band_sigma_mult':s.band_sigma_mult,'consecutive_bars':s.consecutive_bars,
        'boundary_policy':'half_open_exclude_straddling','reference_policy':'fixed_interval_median_close'},
      'time_context':{'event_publication_ts':iso(t),'event_receipt_ts':iso(s.receipt),'data_retrieval_ts':iso(s.retrieval),
        'observation_end_ts':iso(t+timedelta(seconds=s.observation_seconds)),
        'reference_interval_start_ts':iso(t+timedelta(seconds=s.reference_start_seconds)),
        'reference_interval_end_ts':iso(t+timedelta(seconds=s.reference_end_seconds)),
        'excluded_straddling_intervals':excluded},
      'coverage_status':'COMPLETE' if complete else 'INCOMPLETE',
      'coverage_missing_by_role':{r:[iso(x) for x in xs] for r,xs in missing.items()},
      'gate_status':g,'gate_reason':reason,'gate_direction':direction,'reference_status':ref_status,
      'stabilization_status':stability,'result_information_status':'RECORDED_AVAILABILITY' if available is not None else 'HISTORICAL_AVAILABILITY_UNKNOWN',
      'sigma_pre':sigma,'z_score':z,'reference_price':reference,'event_type':kind,'news_weight':weight,
      'reference_bar_count':len(gs['REFERENCE'])-len(missing['REFERENCE']),
      'candidate_bar_count':len(gs['OBSERVATION'])-len(missing['OBSERVATION']),
      'candidate_bar_open_ts':iso(first),'candidate_bar_close_ts':iso(first+step) if first is not None else None,
      'confirmation_bar_open_ts':iso(last),'confirmation_bar_close_ts':iso(last+step) if last is not None else None,
      'candidate_close_delay_seconds':(first+step-t).total_seconds() if first is not None else None,
      'confirmation_close_delay_seconds':(last+step-t).total_seconds() if last is not None else None,
      'reference_close_lower_bound_ts':iso(max(gs['REFERENCE'])+step) if reference is not None else None,
      'result_available_lower_bound_ts':iso(lower),'result_available_ts':iso(available),
      'required_input_roles':['PRE','MOVE','OBSERVATION','REFERENCE'],
      'availability_assumption':'recorded_only'}
    assert set(record)==set(RESULT_FIELDS)
    return {k:record[k] for k in RESULT_FIELDS}
