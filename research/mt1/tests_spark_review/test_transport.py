import copy,json,sys,unittest
from dataclasses import replace
from med_timing import evaluate
from med_timing.contracts import RESULT_FIELDS
from med_timing_spark import encode_study,evaluate_wire
from med_timing_spark.adapter import _coerce,MAX_WIRE_BYTES
from med_timing_spark.schema import RESULT,ENVELOPE
from tests_timing.test_mt1 import spec,fixture,T
from .cases import scenarios

class TransportTests(unittest.TestCase):
    def test_all_scenarios_exact_against_reviewed_python(self):
        for name,s,b in scenarios():
            with self.subTest(name=name):
                original=evaluate(s,b);wrapped=evaluate_wire(encode_study(s,b))
                if original['schema_version']=='mt1.validation_error':
                    self.assertEqual(wrapped,{'schema_version':'mt1.validation_error','result':None,'errors':original['errors']})
                else:
                    self.assertEqual(wrapped,{'schema_version':'mt1.study_result','result':original,'errors':[]})
    def test_negative_no_streak_preserved(self):
        _,s,b=scenarios()[1];r=evaluate_wire(encode_study(s,b))['result']
        self.assertEqual((r['gate_status'],r['stabilization_status']),('NOT_TRIGGERED','NOT_STABILIZED_BY_HORIZON'))
        self.assertIsNone(r['candidate_close_delay_seconds'])
    def test_schema_field_order_equals_reviewed_contract(self):self.assertEqual(tuple(n for n,_,_ in RESULT),RESULT_FIELDS)
    def test_schema_names_unique_recursively(self):
        def visit(d):
            if isinstance(d,list):
                self.assertEqual(len(d),len({n for n,_,_ in d}))
                for _,kind,_ in d:visit(kind)
            elif isinstance(d,tuple):visit(d[1])
            else:self.assertIn(d,{'long','double','string'})
        visit(ENVELOPE)
    def test_bad_wire_inputs_are_transport_errors(self):
        for value in [None,1,'','{}','null','[]','{"x":1,"x":2}','NaN','"'+('x'*10)+'"','[']:
            with self.subTest(value=value):
                r=evaluate_wire(value);self.assertEqual(r['schema_version'],'mt1.spark_transport_error');self.assertIsNone(r['result'])
    def test_wire_size_cap(self):self.assertEqual(evaluate_wire('x'*(MAX_WIRE_BYTES+1))['schema_version'],'mt1.spark_transport_error')
    def test_wrong_wire_version_rejected(self):
        x=json.loads(encode_study(spec(),fixture()));x['wire_version']='future';self.assertEqual(evaluate_wire(json.dumps(x))['schema_version'],'mt1.spark_transport_error')
    def test_extra_nested_field_rejected(self):
        x=json.loads(encode_study(spec(),fixture()));x['bars'][0]['new']=1;self.assertEqual(evaluate_wire(json.dumps(x))['schema_version'],'mt1.spark_transport_error')
    def test_bad_timestamp_rejected_without_payload_leak(self):
        x=json.loads(encode_study(spec(),fixture()));x['study']['publication']='SECRET_INVALID_TS';r=evaluate_wire(json.dumps(x));self.assertNotIn('SECRET',str(r));self.assertEqual(r['schema_version'],'mt1.spark_transport_error')
    def test_nonfinite_wire_token_rejected(self):
        x=encode_study(spec(),fixture()).replace('100.0','NaN',1);self.assertEqual(evaluate_wire(x)['schema_version'],'mt1.spark_transport_error')
    def test_serializer_rejects_nonfinite(self):
        b=fixture();b[0]=replace(b[0],close=float('nan'))
        with self.assertRaises(ValueError):encode_study(spec(),b)
    def test_integer_to_double_coercion_only(self):
        r=evaluate_wire(encode_study(spec(),[replace(b,open=100,high=100,low=100,close=100,volume=1) for b in fixture()]))['result']
        self.assertIsInstance(r['sigma_pre'],float);self.assertIsInstance(r['reference_price'],float)
        self.assertIsInstance(r['candidate_bar_count'],int)
    def test_schema_drift_raises_not_false_negative(self):
        r=evaluate(spec(),fixture());r['surprise']=1
        with self.assertRaises(ValueError):_coerce(r,RESULT)
    def test_null_required_field_raises(self):
        r=evaluate(spec(),fixture());r['gate_status']=None
        with self.assertRaises(ValueError):_coerce(r,RESULT)
    def test_encode_preserves_inputs(self):
        s=spec();b=fixture();before=copy.deepcopy(b);encode_study(s,b);self.assertEqual(b,before)
    def test_offsets_normalize_through_evaluator(self):
        from datetime import timezone,timedelta
        s=spec(publication=T.astimezone(timezone(timedelta(hours=5,minutes=30))))
        self.assertEqual(evaluate_wire(encode_study(s,fixture(s)))['result']['time_context']['event_publication_ts'],'2026-10-07T18:00:00+00:00')
    def test_no_spark_import_needed(self):self.assertNotIn('pyspark',sys.modules)

if __name__=='__main__':unittest.main()
