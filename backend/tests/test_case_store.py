"""The outbound case repository preserves immutable snapshots and ID sequencing."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

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

    def test_missing_generated_id_fails_without_storing_or_consuming_id(self):
        connection = MagicMock()
        connection.execute.return_value.inserted_primary_key = None
        transaction = MagicMock()
        transaction.__enter__.return_value = connection
        transaction.__exit__.return_value = False

        with (
            patch.object(self.store.engine, 'begin', return_value=transaction),
            self.assertRaisesRegex(RuntimeError, 'database returned no case ID'),
        ):
            self.store.save({'density_kg_m3': 1000}, {'pressure_pa': 1200})

        transaction.__exit__.assert_called_once()
        self.assertIsInstance(transaction.__exit__.call_args.args[1], RuntimeError)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(self.store.save({'density_kg_m3': 1000}, {})['id'], 1)
