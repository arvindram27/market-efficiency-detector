"""Bounded one-study-per-row Spark transport adapter, not native Spark math.
Pure Python evaluate is intentionally reused unchanged. No file/network/session
operations occur on import. Malformed wire rows become explicit transport errors;
Python study-validation envelopes remain distinguishable from transport errors.
"""
import json
import math
from dataclasses import asdict,fields
from datetime import datetime
from med_timing import Bar,Study,evaluate
from .schema import RESULT,ENVELOPE

WIRE_VERSION='mt1.spark_wire.v1'
MAX_WIRE_BYTES=8*1024*1024
MAX_BARS=10000

def _default(value):
    if isinstance(value,datetime):return value.isoformat()
    raise TypeError('unsupported serialization value')

def encode_study(study,bars):
    """Serialize a typed study for Spark. No evaluation or I/O.
    Intended for Study/Bar values within the reviewed finite input domain.
    Raw malformed rows can be passed directly for transport-error tests.
    """
    if not isinstance(study,Study) or not isinstance(bars,(list,tuple)) or len(bars)>MAX_BARS:
        raise ValueError('wire input type/count')
    if any(not isinstance(b,Bar) for b in bars):raise ValueError('wire bar type')
    text=json.dumps({'wire_version':WIRE_VERSION,'study':asdict(study),
        'bars':[asdict(b) for b in bars]},default=_default,allow_nan=False,
        separators=(',',':'),sort_keys=True)
    if len(text.encode('utf-8'))>MAX_WIRE_BYTES:raise ValueError('wire byte cap')
    return text

def _pairs(items):
    out={}
    for key,value in items:
        if key in out:raise ValueError('duplicate key')
        out[key]=value
    return out

def _constant(value):raise ValueError('nonfinite token')

def _object(value,cls):
    if not isinstance(value,dict) or set(value)!={f.name for f in fields(cls)}:
        raise ValueError('wire field set')
    value=dict(value)
    names=('publication','receipt','retrieval') if cls is Study else ('open_ts','available_ts')
    for name in names:
        if value[name] is not None:
            if not isinstance(value[name],str):raise ValueError('wire timestamp type')
            value[name]=datetime.fromisoformat(value[name])
    return cls(**value)

def _coerce(value,descriptor):
    """Avoid Spark DoubleType rejecting legitimate Python integer prices/zeros.
    Also reject accidental schema drift before crossing the UDF boundary.
    """
    if isinstance(descriptor,list):
        if not isinstance(value,dict) or set(value)!={n for n,_,_ in descriptor}:
            raise ValueError('result field drift')
        out={}
        for name,kind,nullable in descriptor:
            item=value[name]
            if item is None:
                if not nullable:raise ValueError('unexpected null')
                out[name]=None
            else:out[name]=_coerce(item,kind)
        return out
    if isinstance(descriptor,tuple):
        if not isinstance(value,list):raise ValueError('array type')
        return [_coerce(x,descriptor[1]) for x in value]
    if descriptor=='string':
        if not isinstance(value,str):raise ValueError('string type')
        return value
    if descriptor=='long':
        if isinstance(value,bool) or not isinstance(value,int) or not -(2**63)<=value<2**63:
            raise ValueError('long type/range')
        return value
    if descriptor=='double':
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('double type/range')
        return float(value)
    raise ValueError('unknown descriptor')

def evaluate_wire(text):
    """Stable errors omit the input/exception text, preventing payload leakage.
    Decode failures never masquerade as a negative study outcome. Unexpected
    evaluator/schema faults raise and fail the Spark action rather than hiding.
    """
    try:
        if not isinstance(text,str) or len(text)>MAX_WIRE_BYTES or len(text.encode('utf-8'))>MAX_WIRE_BYTES:
            raise ValueError('wire type/cap')
        doc=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
        if not isinstance(doc,dict) or set(doc)!={'wire_version','study','bars'} or doc['wire_version']!=WIRE_VERSION:
            raise ValueError('wire envelope')
        if not isinstance(doc['bars'],list) or len(doc['bars'])>MAX_BARS:raise ValueError('wire count')
        study=_object(doc['study'],Study)
        bars=[_object(b,Bar) for b in doc['bars']]
    except (ValueError,TypeError,OverflowError,RecursionError):
        return _coerce({'schema_version':'mt1.spark_transport_error','result':None,
            'errors':[{'code':'INVALID_WIRE','field':'wire','interval_open_ts':None}]},ENVELOPE)
    record=evaluate(study,bars)
    if record['schema_version']=='mt1.validation_error':
        return _coerce({'schema_version':record['schema_version'],'result':None,'errors':record['errors']},ENVELOPE)
    return _coerce({'schema_version':'mt1.study_result','result':record,'errors':[]},ENVELOPE)

def apply_studies(frame,wire_column='wire_json',output_column='mt1'):
    """Return a lazy DataFrame with a single structured mt1 column appended.
    Caller owns session, source rows, stable IDs and execution authorization.
    No session creation, collection, ordering, writes or package installation.
    """
    from pyspark.sql import functions as F,types as T
    from .schema import output_schema
    if not isinstance(wire_column,str) or not isinstance(output_column,str) or not output_column:
        raise ValueError('column names')
    if frame.columns.count(wire_column)!=1 or output_column in frame.columns:
        raise ValueError('ambiguous/missing input or output collision')
    if not isinstance(frame.schema[wire_column].dataType,T.StringType):raise ValueError('wire column must be string')
    return frame.withColumn(output_column,F.udf(evaluate_wire,output_schema(),useArrow=False)(frame[wire_column]))
