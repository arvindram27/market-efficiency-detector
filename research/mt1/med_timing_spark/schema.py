"""Explicit wire schema. ISO UTC timestamps deliberately remain strings.
No Spark import or session/action on import. A result is the unchanged mt1 record.
"""
# (name, type, nullable). Arrays never contain null elements.
PARAMETERS = [(n, 'long', False) for n in (
    'interval_seconds','pre_bars','move_seconds','observation_seconds',
    'reference_start_offset_seconds','reference_end_offset_seconds')]+[
    ('z_threshold','double',False),('band_sigma_mult','double',False),
    ('consecutive_bars','long',False),('boundary_policy','string',False),
    ('reference_policy','string',False)]
STRADDLE=[('bar_open_ts','string',False),('bar_close_ts','string',False),
          ('lost_pre_seconds','double',False),('lost_post_seconds','double',False)]
TIME_CONTEXT=[('event_publication_ts','string',False),('event_receipt_ts','string',True),
    ('data_retrieval_ts','string',True),('observation_end_ts','string',False),
    ('reference_interval_start_ts','string',False),('reference_interval_end_ts','string',False),
    ('excluded_straddling_intervals',('array',STRADDLE),False)]
MISSING=[(n,('array','string'),False) for n in ('PRE','MOVE','OBSERVATION','REFERENCE')]
RESULT=[(n,'string',False) for n in (
    'schema_version','study_id','ticker','source_url','exact_headline','data_vintage',
    'input_sha256','algorithm_version')]+[
    ('source_revision','string',True),('parameters',PARAMETERS,False),
    ('time_context',TIME_CONTEXT,False),('coverage_status','string',False),
    ('coverage_missing_by_role',MISSING,False),('gate_status','string',False),
    ('gate_reason','string',True),('gate_direction','string',False),
    ('reference_status','string',False),('stabilization_status','string',False),
    ('result_information_status','string',False),('sigma_pre','double',True),
    ('z_score','double',True),('reference_price','double',True),
    ('event_type','string',False),('news_weight','string',False),
    ('reference_bar_count','long',False),('candidate_bar_count','long',False)]+[
    (n,'string',True) for n in ('candidate_bar_open_ts','candidate_bar_close_ts',
        'confirmation_bar_open_ts','confirmation_bar_close_ts')]+[
    ('candidate_close_delay_seconds','double',True),('confirmation_close_delay_seconds','double',True),
    ('reference_close_lower_bound_ts','string',True),('result_available_lower_bound_ts','string',True),
    ('result_available_ts','string',True),('required_input_roles',('array','string'),False),
    ('availability_assumption','string',False)]
ERROR=[('code','string',False),('field','string',False),('interval_open_ts','string',True)]
ENVELOPE=[('schema_version','string',False),('result',RESULT,True),
          ('errors',('array',ERROR),False)]

def spark_type(descriptor):
    from pyspark.sql import types as T
    if isinstance(descriptor,list):
        return T.StructType([T.StructField(n,spark_type(t),null) for n,t,null in descriptor])
    if isinstance(descriptor,tuple):
        kind,item=descriptor
        if kind!='array':raise ValueError('unknown descriptor')
        return T.ArrayType(spark_type(item),containsNull=False)
    return {'string':T.StringType,'double':T.DoubleType,'long':T.LongType}[descriptor]()

def output_schema():return spark_type(ENVELOPE)
