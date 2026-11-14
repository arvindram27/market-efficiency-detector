import json
import math
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from statistics import stdev
from med_timing import Study,Bar,evaluate
from med_timing.contracts import RESULT_FIELDS
from med_timing.validation import grids,iso
from med_timing.retrospective import first_streak,gate,classify

UTC=timezone.utc
T=datetime(2026,10,7,18,tzinfo=UTC)
STEP=timedelta(minutes=1)
HEADLINE='Minutes of the Federal Open Market Committee, September 15-16, 2026'

def spec(**kw):
    s=Study(T,HEADLINE,'SYNTH','test','https://example.invalid/event','synthetic','0'*64)
    return replace(s,**kw)

def bar(t,close,arrival=None):
    return Bar(t,close,close,close,close,1.0,arrival)

def fixture(s=None,arrivals=False):
    s=s or spec();gs=grids(s);value=100.0;pre=[]
    for i,x in enumerate(gs['PRE']):
        if i:value*=math.exp(.01 if i%2 else -.01)
        pre.append(bar(x,value,x+STEP+timedelta(seconds=10) if arrivals else None))
    obs=[bar(x,100.0,x+STEP+timedelta(seconds=10) if arrivals else None) for x in gs['OBSERVATION']]
    return pre+obs

def edit(bars,t,**kw):
    return [replace(b,**kw) if b.open_ts==t else b for b in bars]

class ContractTests(unittest.TestCase):
    def test_exact_schema_order_and_json_finite(self):
        r=evaluate(spec(),fixture());self.assertEqual(tuple(r),RESULT_FIELDS)
        json.dumps(r,allow_nan=False)
    def test_five_move_ninety_observation_twenty_reference(self):
        gs=grids(spec());self.assertEqual([len(gs[k]) for k in ('PRE','MOVE','OBSERVATION','REFERENCE')],[60,5,90,20])
        self.assertEqual(gs['REFERENCE'][0],T+timedelta(minutes=70));self.assertEqual(gs['REFERENCE'][-1]+STEP,T+timedelta(minutes=90))
    def test_early_pattern_separate_from_late_information(self):
        r=evaluate(spec(),fixture());self.assertEqual(r['stabilization_status'],'CONFIRMED')
        self.assertEqual(r['candidate_close_delay_seconds'],60);self.assertEqual(r['confirmation_close_delay_seconds'],300)
        self.assertEqual(r['candidate_bar_open_ts'],iso(T));self.assertEqual(r['confirmation_bar_open_ts'],iso(T+4*STEP))
        self.assertEqual(r['result_available_lower_bound_ts'],iso(T+90*STEP));self.assertIsNone(r['result_available_ts'])
    def test_sigma_uses_59_returns(self):
        r=evaluate(spec(),fixture());want=stdev([.01 if i%2 else -.01 for i in range(1,60)])
        self.assertAlmostEqual(r['sigma_pre'],want,places=14)
    def test_gate_failure_does_not_erase_stability(self):
        r=evaluate(spec(),fixture());self.assertEqual(r['gate_status'],'NOT_TRIGGERED')
        self.assertEqual(r['gate_reason'],'NO_PRICE_MOVE');self.assertEqual(r['stabilization_status'],'CONFIRMED')
    def test_delayed_reference_arrival_controls_full_result(self):
        s=spec(receipt=T+timedelta(seconds=2));bars=fixture(s,True)
        bars=edit(bars,T+79*STEP,available_ts=T+92*STEP)
        r=evaluate(s,bars);self.assertEqual(r['result_available_ts'],iso(T+92*STEP))
        self.assertEqual(r['result_information_status'],'RECORDED_AVAILABILITY')
    def test_unknown_one_arrival_keeps_result_unknown(self):
        s=spec(receipt=T);bars=fixture(s,True);bars=edit(bars,T+20*STEP,available_ts=None)
        self.assertIsNone(evaluate(s,bars)['result_available_ts'])
    def test_unknown_receipt_stays_unknown(self):
        self.assertIsNone(evaluate(spec(),fixture(arrivals=True))['result_available_ts'])
    def test_incomplete_result_has_no_full_information_bound(self):
        bars=[b for b in fixture() if b.open_ts!=T+20*STEP];r=evaluate(spec(),bars)
        self.assertEqual(r['stabilization_status'],'INSUFFICIENT_OBSERVATION_COVERAGE')
        self.assertIsNone(r['result_available_lower_bound_ts']);self.assertIsNotNone(r['reference_close_lower_bound_ts'])
    def test_missing_reference_not_shortened(self):
        r=evaluate(spec(),[b for b in fixture() if b.open_ts!=T+80*STEP])
        self.assertEqual(r['reference_status'],'UNAVAILABLE_COVERAGE');self.assertEqual(r['stabilization_status'],'UNAVAILABLE_REFERENCE')
        self.assertIsNone(r['reference_price'])
    def test_missing_pre_not_partial_sigma(self):
        r=evaluate(spec(),fixture()[1:]);self.assertIsNone(r['sigma_pre']);self.assertIsNone(r['z_score'])
        self.assertEqual(r['gate_status'],'UNAVAILABLE_COVERAGE');self.assertEqual(r['stabilization_status'],'UNAVAILABLE_PRE_SCALE')
    def test_zero_scale_is_not_zero_move(self):
        bars=[bar(b.open_ts,100) for b in fixture()];r=evaluate(spec(),bars)
        self.assertEqual(r['sigma_pre'],0);self.assertIsNone(r['z_score']);self.assertEqual(r['gate_status'],'UNAVAILABLE_SCALE')
    def test_straddling_boundary_and_330second_confirmation(self):
        s=spec(publication=T+timedelta(seconds=30));bars=fixture(s)+[bar(T,100)]
        r=evaluate(s,bars);self.assertEqual(r['candidate_close_delay_seconds'],90);self.assertEqual(r['confirmation_close_delay_seconds'],330)
        self.assertEqual(len(grids(s)['MOVE']),4)
        loss=r['time_context']['excluded_straddling_intervals'][0];self.assertEqual(loss['lost_pre_seconds'],30);self.assertEqual(loss['lost_post_seconds'],30)
    def test_boundary_pre_close_and_post_open(self):
        gs=grids(spec());self.assertEqual(gs['PRE'][-1]+STEP,T);self.assertEqual(gs['OBSERVATION'][0],T)
    def test_extra_after_horizon_cannot_change_metrics(self):
        r=evaluate(spec(),fixture());r2=evaluate(spec(),fixture()+[bar(T+90*STEP,10000)])
        self.assertEqual(r,r2)
    def test_reference_overlap_allowed(self):
        r=evaluate(spec(),fixture());self.assertEqual(r['schema_version'],'mt1.study_result')
        self.assertEqual(r['reference_bar_count'],20)
    def test_reference_change_can_change_expost_pattern(self):
        bars=fixture();r=evaluate(spec(),bars)
        changed=[bar(b.open_ts,110) if b.open_ts>=T+70*STEP else b for b in bars]
        r2=evaluate(spec(),changed);self.assertNotEqual(r['reference_price'],r2['reference_price']);self.assertNotEqual(r['candidate_bar_open_ts'],r2['candidate_bar_open_ts'])
    def test_reference_interval_outside_rejected(self):
        r=evaluate(spec(reference_end_seconds=5460),fixture());self.assertEqual(r['schema_version'],'mt1.validation_error')
    def test_shuffled_input_same_result(self):
        self.assertEqual(evaluate(spec(),fixture()),evaluate(spec(),list(reversed(fixture()))))
    def test_source_revision_not_fabricated(self):
        self.assertIsNone(evaluate(spec(),fixture())['source_revision'])

class RuleTests(unittest.TestCase):
    def test_v1_and_v3_rules(self):
        opens=[T+i*STEP for i in range(8)];cs=[100,100.1,101,100.5,99.5,100,100.2,99.8]
        by={x:bar(x,c) for x,c in zip(opens,cs)}
        first,last=first_streak(opens,by,100,.01,.5,5);self.assertEqual((first,last),(T+3*STEP,T+7*STEP))
    def test_no_streak_vector(self):
        bars=fixture();bars=[bar(b.open_ts,99 if int((b.open_ts-T).total_seconds()/60)%2 else 101) if b.open_ts>=T else b for b in bars]
        r=evaluate(spec(),bars);self.assertEqual(r['reference_price'],100);self.assertEqual(r['stabilization_status'],'NOT_STABILIZED_BY_HORIZON')
        for f in ('candidate_bar_open_ts','confirmation_bar_close_ts','candidate_close_delay_seconds'):self.assertIsNone(r[f])
    def test_gate_equality_strict(self):
        self.assertEqual(gate(2,'MACRO','HIGH',2)[0],'NOT_TRIGGERED');self.assertEqual(gate(-2.0001,'MACRO','HIGH',2),('TRIGGERED',None,'SHORT'))
    def test_exact_taxonomy(self):
        self.assertEqual(classify(HEADLINE),('MACRO','HIGH'));self.assertEqual(classify('Ordinary product announcement'),('OTHER','LOW'))

class ErrorTests(unittest.TestCase):
    def codes(self,r):return {e['code'] for e in r['errors']}
    def test_duplicate_rejected(self):
        b=fixture();r=evaluate(spec(),b+[b[0]]);self.assertIn('DUPLICATE_TIMESTAMP',self.codes(r))
        self.assertNotIn('z_score',r)
    def test_nonfinite_rejected(self):
        b=fixture();b[0]=replace(b[0],close=float('nan'));self.assertIn('NONFINITE_VALUE',self.codes(evaluate(spec(),b)))
    def test_invalid_ohlc_rejected(self):
        b=fixture();b[0]=replace(b[0],low=200);self.assertIn('INVALID_OHLCV',self.codes(evaluate(spec(),b)))
    def test_arrival_before_close_rejected(self):
        b=fixture();b[0]=replace(b[0],available_ts=b[0].open_ts);self.assertIn('INVALID_AVAILABILITY',self.codes(evaluate(spec(),b)))
    def test_receipt_before_publication_rejected(self):
        self.assertIn('INVALID_AVAILABILITY',self.codes(evaluate(spec(receipt=T-STEP),fixture())))
    def test_naive_timestamp_rejected(self):
        self.assertIn('INVALID_TIMESTAMP',self.codes(evaluate(spec(publication=T.replace(tzinfo=None)),fixture())))
    def test_offgrid_rejected(self):
        b=fixture();b[0]=replace(b[0],open_ts=b[0].open_ts+timedelta(seconds=1));self.assertIn('OFF_GRID_TIMESTAMP',self.codes(evaluate(spec(),b)))
    def test_error_order_deterministic(self):
        b=fixture();b[0]=replace(b[0],close=float('inf'));b[1]=replace(b[1],volume=-1)
        self.assertEqual(evaluate(spec(),b),evaluate(spec(),list(reversed(b))))
    def test_no_write_no_input_mutation(self):
        b=fixture();original=list(b);evaluate(spec(),b);self.assertEqual(b,original)
    def test_caps_and_boolean_spec_rejected(self):
        self.assertIn('INVALID_SPEC',self.codes(evaluate(spec(interval_seconds=True),fixture())))
        self.assertIn('INVALID_SPEC',self.codes(evaluate(spec(),fixture()*100)))

class AdditionalTests(unittest.TestCase):
    def test_no_stability_can_coexist_with_no_gate(self):
        # Rule-unit assertion keeps this independent of a tuned price path.
        self.assertEqual(gate(0,'MACRO','HIGH',2)[0],'NOT_TRIGGERED')
        opens=[T+i*STEP for i in range(90)]
        by={x:bar(x,99 if i%2 else 101) for i,x in enumerate(opens)}
        self.assertEqual(first_streak(opens,by,100,.01,.5,5),(None,None))
    def test_very_large_finite_prices_do_not_overflow_ratios(self):
        b=fixture();b[0]=bar(b[0].open_ts,1e-100);b[1]=bar(b[1].open_ts,1e100)
        r=evaluate(spec(),b);json.dumps(r,allow_nan=False)
        self.assertEqual(r['schema_version'],'mt1.study_result')
    def test_unrepresentable_integer_is_rejected(self):
        b=fixture();b[0]=replace(b[0],volume=10**1000)
        self.assertIn('NONFINITE_VALUE',{x['code'] for x in evaluate(spec(),b)['errors']})
    def test_extra_bad_candle_still_rejected_structurally(self):
        r=evaluate(spec(),fixture()+[bar(T+90*STEP,float('nan'))])
        self.assertEqual(r['schema_version'],'mt1.validation_error')
    def test_unknown_receipt_is_never_retrieval(self):
        s=spec(retrieval=T+timedelta(days=40));r=evaluate(s,fixture(s,True))
        self.assertIsNone(r['result_available_ts']);self.assertIsNone(r['time_context']['event_receipt_ts'])
    def test_duplicate_and_nonfinite_codes_both_preserved(self):
        b=fixture();b.append(replace(b[0],volume=float('inf')))
        codes={x['code'] for x in evaluate(spec(),b)['errors']}
        self.assertEqual(codes,{'DUPLICATE_TIMESTAMP','NONFINITE_VALUE'})
    def test_revision_is_optional_not_an_arbitrary_label(self):
        r=evaluate(spec(source_revision='not verified'),fixture())
        self.assertEqual(r['schema_version'],'mt1.validation_error')

class DerivedNumericTests(unittest.TestCase):
    def test_unsupported_large_reference_rejected(self):
        b=[bar(x.open_ts,1e308) if x.open_ts>=T else x for x in fixture()]
        r=evaluate(spec(),b);self.assertEqual(r['schema_version'],'mt1.validation_error')
    def test_out_of_range_prices_cannot_form_pattern(self):
        b=fixture();b[0]=bar(b[0].open_ts,1e-100);b[1]=bar(b[1].open_ts,1e100)
        b=[bar(x.open_ts,1e308) if x.open_ts>=T else x for x in b]
        r=evaluate(spec(),b);self.assertEqual(r['schema_version'],'mt1.validation_error')
        self.assertTrue(any(x['code']=='INVALID_OHLCV' for x in r['errors']))

class TimestampAndRangeTests(unittest.TestCase):
    def test_datetime_max_bar_is_error_not_exception(self):
        b=fixture();b.append(bar(datetime.max.replace(tzinfo=UTC),100))
        self.assertEqual(evaluate(spec(),b)['schema_version'],'mt1.validation_error')
    def test_utc_conversion_overflow_is_rejected(self):
        extreme=datetime.max.replace(tzinfo=timezone(timedelta(hours=-12)))
        for name in ('publication','receipt','retrieval'):
            self.assertEqual(evaluate(spec(**{name:extreme}),fixture())['schema_version'],'mt1.validation_error')
        b=fixture();b[0]=replace(b[0],available_ts=extreme)
        self.assertEqual(evaluate(spec(),b)['schema_version'],'mt1.validation_error')
    def test_minimum_datetime_conversion_is_rejected(self):
        extreme=datetime.min.replace(tzinfo=timezone(timedelta(hours=12)))
        self.assertEqual(evaluate(spec(publication=extreme),fixture())['schema_version'],'mt1.validation_error')
    def test_subnormal_price_is_explicitly_unsupported(self):
        b=fixture();b[0]=bar(b[0].open_ts,5e-324)
        self.assertEqual(evaluate(spec(),b)['schema_version'],'mt1.validation_error')
    def test_price_supported_endpoints_remain_finite(self):
        for price in (1e-100,1e100):
            b=[bar(x.open_ts,price) for x in fixture()]
            r=evaluate(spec(),b);self.assertEqual(r['reference_price'],price)
            self.assertEqual(r['gate_status'],'UNAVAILABLE_SCALE');json.dumps(r,allow_nan=False)
    def test_bar_and_arrival_outside_utc_range_rejected(self):
        b=fixture();b[0]=replace(b[0],open_ts=datetime(1999,12,31,tzinfo=UTC))
        self.assertEqual(evaluate(spec(),b)['schema_version'],'mt1.validation_error')
        b=fixture();b[0]=replace(b[0],available_ts=datetime(2101,1,1,tzinfo=UTC))
        self.assertEqual(evaluate(spec(),b)['schema_version'],'mt1.validation_error')

if __name__=='__main__':unittest.main()
