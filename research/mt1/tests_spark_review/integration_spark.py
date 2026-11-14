"""Opt-in synthetic Spark transport checks; not auto-discovered.
No actual fixture or file reads. Uses an already-available compatible runtime.
No session on import. main() explicitly creates/stops a local Spark session.
The initial development run passed these four tests; see docs/verification.md
for its exact scope. A fresh environment still needs its own verification.
"""
import unittest
from med_timing_spark import encode_study,evaluate_wire,apply_studies,output_schema
from .cases import scenarios

class SparkParityTests(unittest.TestCase):
    spark=None
    def test_explicit_full_schema_and_all_fields_after_repartition(self):
        from pyspark.sql import types as T
        records=[(n,encode_study(s,b)) for n,s,b in scenarios()]+[('malformed','{')]
        frame=self.spark.createDataFrame(records,T.StructType([
            T.StructField('case_id',T.StringType(),False),T.StructField('wire_json',T.StringType(),True)]))
        for partitions in (1,3):
            rows=apply_studies(frame.repartition(partitions)).select('case_id','mt1').collect()
            self.assertEqual(len(rows),len(records))
            actual={r['case_id']:r['mt1'].asDict(recursive=True) for r in rows}
            self.assertEqual(len(actual),len(records))
            for name,wire in records:
                with self.subTest(partitions=partitions,case=name):self.assertEqual(actual[name],evaluate_wire(wire))
            self.assertEqual(apply_studies(frame).schema['mt1'].dataType,output_schema())
    def test_session_timezone_cannot_shift_iso_strings(self):
        name,s,b=scenarios()[5];wire=encode_study(s,b)
        from pyspark.sql import types as T
        frame=self.spark.createDataFrame([(wire,)],T.StructType([T.StructField('wire_json',T.StringType(),True)]))
        before=self.spark.conf.get('spark.sql.session.timeZone')
        try:
            for zone in ('UTC','Asia/Kolkata','America/New_York'):
                self.spark.conf.set('spark.sql.session.timeZone',zone)
                actual=apply_studies(frame).select('mt1').collect()[0][0].asDict(recursive=True)
                self.assertEqual(actual,evaluate_wire(wire))
        finally:self.spark.conf.set('spark.sql.session.timeZone',before)
    def test_transport_null_and_empty_frame(self):
        from pyspark.sql import types as T
        schema=T.StructType([T.StructField('wire_json',T.StringType(),True)])
        self.assertEqual(apply_studies(self.spark.createDataFrame([],schema)).count(),0)
        row=apply_studies(self.spark.createDataFrame([(None,)],schema)).select('mt1').collect()[0][0]
        self.assertEqual(row.asDict(recursive=True),evaluate_wire(None))
    def test_bad_column_and_collision_fail_before_action(self):
        frame=self.spark.createDataFrame([('x',)],['wire_json'])
        with self.assertRaises(ValueError):apply_studies(frame,'missing')
        with self.assertRaises(ValueError):apply_studies(frame,output_column='wire_json')
        ints=self.spark.createDataFrame([(1,)],['wire_json'])
        with self.assertRaises(ValueError):apply_studies(ints)

def main():
    from pyspark.sql import SparkSession
    spark=SparkSession.builder.master('local[2]').appName('mt1-synthetic-transport-review').getOrCreate()
    SparkParityTests.spark=spark
    try:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SparkParityTests))
        return 0 if result.wasSuccessful() and result.testsRun==4 else 2
    finally:spark.stop()

if __name__=='__main__':raise SystemExit(main())
