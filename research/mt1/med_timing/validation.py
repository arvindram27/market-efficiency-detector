"""Deterministic validation and expected grids, with no I/O or repairs."""
import math
from datetime import datetime, timedelta, timezone
from .contracts import Bar, Study

UTC = timezone.utc

def aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None

def supported_time(value):
    try:
        return aware(value) and 2000 <= value.astimezone(UTC).year <= 2100
    except (OverflowError, ValueError):
        return False

def iso(value):
    return value.astimezone(UTC).isoformat() if value is not None else None

def finite_number(value):
    try:
        return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False

def error(code, field, at=None):
    return {'code': code, 'field': field, 'interval_open_ts': iso(at) if aware(at) else None}

def envelope(errors):
    unique = {(x['interval_open_ts'] or '', x['field'], x['code']): x for x in errors}
    return {'schema_version':'mt1.validation_error', 'errors':[unique[k] for k in sorted(unique)]}

def grid_contained(start, end, seconds):
    # All provider candle opens lie on the UTC epoch interval grid.
    first = math.ceil(start.timestamp()/seconds)*seconds
    out = []
    at = datetime.fromtimestamp(first, UTC)
    while at + timedelta(seconds=seconds) <= end:
        out.append(at); at += timedelta(seconds=seconds)
    return out

def validate_spec(s):
    errors=[]
    if not isinstance(s, Study):
        return [error('INVALID_SPEC','study')]
    for name in ('publication','receipt','retrieval'):
        t=getattr(s,name)
        if (t is None and name=='publication') or (t is not None and not supported_time(t)):
            errors.append(error('INVALID_TIMESTAMP',name))
    if errors: return errors
    if not supported_time(s.publication):
        errors.append(error('INVALID_SPEC','prototype_date_range'))
    if s.source_revision is not None and (not isinstance(s.source_revision,str) or len(s.source_revision)!=40 or any(c not in '0123456789abcdef' for c in s.source_revision)):
        errors.append(error('INVALID_SPEC','source_revision'))
    if s.receipt is not None and s.receipt < s.publication:
        errors.append(error('INVALID_AVAILABILITY','event_receipt_ts'))
    for name in ('interval_seconds','pre_bars','move_seconds','observation_seconds','reference_start_seconds','reference_end_seconds','consecutive_bars'):
        v=getattr(s,name)
        if isinstance(v,bool) or not isinstance(v,int) or v<0:
            errors.append(error('INVALID_SPEC',name))
    for name in ('z_threshold','band_sigma_mult'):
        v=getattr(s,name)
        if not finite_number(v) or v<=0:
            errors.append(error('INVALID_SPEC',name))
    if errors:return errors
    # Prototype is deliberately bounded to the accepted minute study parameters.
    if (s.interval_seconds,s.pre_bars,s.move_seconds,s.observation_seconds,
        s.reference_start_seconds,s.reference_end_seconds,s.consecutive_bars,
        s.z_threshold,s.band_sigma_mult)!=(60,60,300,5400,4200,5400,5,2.0,0.5):
        errors.append(error('INVALID_SPEC','prototype_parameters'))
    for name in ('headline','ticker','study_id','source_url','data_vintage','input_sha256'):
        if not isinstance(getattr(s,name),str) or not getattr(s,name).strip():errors.append(error('INVALID_SPEC',name))
    if not isinstance(s.input_sha256,str) or len(s.input_sha256)!=64 or any(c not in '0123456789abcdef' for c in s.input_sha256):
        errors.append(error('INVALID_SPEC','input_sha256'))
    return errors

def grids(s):
    t=s.publication.astimezone(UTC); step=timedelta(seconds=s.interval_seconds)
    last_close=datetime.fromtimestamp(math.floor(t.timestamp()/s.interval_seconds)*s.interval_seconds,UTC)
    pre=[last_close-step*i for i in range(s.pre_bars,0,-1)]
    obs=grid_contained(t,t+timedelta(seconds=s.observation_seconds),s.interval_seconds)
    move=grid_contained(t,t+timedelta(seconds=s.move_seconds),s.interval_seconds)
    ref=grid_contained(t+timedelta(seconds=s.reference_start_seconds),t+timedelta(seconds=s.reference_end_seconds),s.interval_seconds)
    return {'PRE':pre,'MOVE':move,'OBSERVATION':obs,'REFERENCE':ref}

def validate_bars(bars,s):
    errors=[];seen=set()
    if not isinstance(bars,(list,tuple)) or len(bars)>10000:
        return [error('INVALID_SPEC','bars_or_input_cap')]
    step=timedelta(seconds=s.interval_seconds)
    for i,b in enumerate(bars):
        if not isinstance(b,Bar):errors.append(error('INVALID_OHLCV',f'bars[{i}]'));continue
        if not supported_time(b.open_ts):errors.append(error('INVALID_TIMESTAMP','bar_open_ts'));continue
        t=b.open_ts.astimezone(UTC)
        if t in seen:errors.append(error('DUPLICATE_TIMESTAMP','bar_open_ts',t))
        seen.add(t)
        if t.timestamp()%s.interval_seconds!=0:errors.append(error('OFF_GRID_TIMESTAMP','bar_open_ts',t))
        invalid=False
        for name in ('open','high','low','close','volume'):
            x=getattr(b,name)
            if isinstance(x,bool) or not isinstance(x,(int,float)):
                errors.append(error('INVALID_OHLCV',name,t));invalid=True
            elif not finite_number(x):errors.append(error('NONFINITE_VALUE',name,t));invalid=True
            elif x<=0 or (name!='volume' and not 1e-100 <= x <= 1e100):errors.append(error('INVALID_OHLCV',name,t));invalid=True
        if not invalid and not (b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high):
            errors.append(error('INVALID_OHLCV','OHLC_order',t))
        if b.available_ts is not None:
            if not supported_time(b.available_ts):errors.append(error('INVALID_TIMESTAMP','bar_available_ts',t))
            elif b.available_ts<t+step:errors.append(error('INVALID_AVAILABILITY','bar_available_ts',t))
    return errors
