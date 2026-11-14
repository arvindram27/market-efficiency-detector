"""Synthetic example checks only; no Spark or private fixture imports."""
import contextlib,io,json,unittest
from synthetic_demo import make_case,main
from med_timing import evaluate

class DemoTests(unittest.TestCase):
    def test_stable_is_independent_of_no_gate(self):
        s,b=make_case('stable');r=evaluate(s,b)
        self.assertEqual((r['gate_status'],r['stabilization_status']),('NOT_TRIGGERED','CONFIRMED'))
        self.assertIsNone(r['result_available_ts'])
        self.assertEqual((r['candidate_close_delay_seconds'],r['confirmation_close_delay_seconds']),(60,300))
    def test_no_streak_keeps_null_coordinates(self):
        s,b=make_case('no_streak');r=evaluate(s,b)
        self.assertEqual(r['stabilization_status'],'NOT_STABILIZED_BY_HORIZON')
        self.assertIsNone(r['candidate_bar_open_ts']);self.assertIsNone(r['confirmation_close_delay_seconds'])
    def test_missing_reference_is_not_shortened(self):
        s,b=make_case('missing_reference');r=evaluate(s,b)
        self.assertEqual((r['coverage_status'],r['reference_status'],r['stabilization_status']),('INCOMPLETE','UNAVAILABLE_COVERAGE','UNAVAILABLE_REFERENCE'))
        self.assertIsNone(r['reference_price']);self.assertIsNone(r['result_available_lower_bound_ts'])
    def test_main_prints_only_three_json_cases(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(),0)
        records=json.loads(out.getvalue());self.assertEqual([x['case'] for x in records],['stable','no_streak','missing_reference'])
        self.assertTrue(all(x['result_available_ts'] is None for x in records))

if __name__=='__main__':unittest.main()
