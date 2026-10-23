"""The outbound case repository preserves immutable snapshots and ID sequencing."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openoil.adapters.outbound.case_store import CaseStore


class CaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CaseStore(Path(self.temp.name) / 'cases.sqlite3')
        self.store.initialize()
        self.addCleanup(self.store.close)

    def test_save_get_and_list_keep_distinct_snapshots(self):
        first_input = {'density_kg_m3': 1000}
        first_result = {'pressure_pa': 1200}
        first = self.store.save(first_input, first_result, {'model_version': '1.0.0'})
        second = self.store.save({'density_kg_m3': 1100}, {'pressure_pa': 1300})

        self.assertEqual(first, {
            'id': 1, 'input': first_input, 'result': first_result,
            'provenance': {'model_version': '1.0.0'},
        })
        self.assertEqual(second['id'], 2)
        self.assertEqual(self.store.get(1), first)
        self.assertEqual(self.store.list(), [first, second])

    def test_rejected_nonfinite_snapshot_does_not_consume_id(self):
        with self.assertRaises(ValueError):
            self.store.save({'flow_m3_s': float('nan')}, {})

        self.assertEqual(self.store.save({'flow_m3_s': 1}, {})['id'], 1)
