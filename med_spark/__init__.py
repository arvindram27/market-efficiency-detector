"""Additive PySpark + Delta Lake extension for the MED (PAL) project.

Nothing in this package is imported by the v0 ``med`` package, and no v0 file
is changed by it. Import ``med_spark.batch``, ``med_spark.delta_store`` or
``med_spark.demo_batch`` directly; this package __init__ deliberately imports
no Spark code so that importing ``med_spark`` stays cheap.
"""
