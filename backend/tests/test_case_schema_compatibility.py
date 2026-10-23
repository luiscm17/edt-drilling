"""Old SQLite snapshots remain byte-for-byte compatible through public v1 routes."""
from contextlib import closing, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from openoil.main import create_app
from test_api import INPUT, expected_result


class CaseSchemaCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'old.sqlite3'
        # Deliberately non-current input/result and unusual JSON formatting.
        self.old_input = '{ "historical" : true }'
        self.old_result = '{ "legacy_pressure" : 17.25 }'
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE cases (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'input_json TEXT NOT NULL, result_json TEXT NOT NULL)')
            db.execute('INSERT INTO cases VALUES (7, ?, ?)',
                       (self.old_input, self.old_result))
        self.legacy = dict(id=7, input=json.loads(self.old_input),
                           result=json.loads(self.old_result))

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json(), body)

    def assert_old_snapshot_unchanged(self, sequence):
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute(
                'SELECT input_json, result_json, provenance_json FROM cases WHERE id=7'
            ).fetchone(), (self.old_input, self.old_result, None))
            self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(cases)')],
                             ['id', 'input_json', 'result_json', 'provenance_json'])
            self.assertEqual(db.execute(
                'SELECT seq FROM sqlite_sequence WHERE name="cases"'
            ).fetchone(), (sequence,))

    def test_old_schema_restart_idempotence_bytes_and_no_recalculation(self):
        for _ in range(2):
            with TestClient(create_app(self.path)) as client:
                with patch('openoil.application.hydraulics.calculate',
                           side_effect=AssertionError('must not recalculate')):
                    self.assert_response(client.get('/api/v1/cases/7'), 200, self.legacy)
                    self.assert_response(client.get('/api/v1/cases'), 200, [self.legacy])
            self.assert_old_snapshot_unchanged(7)

    def test_calculate_save_next_id_and_restart_without_recalculation(self):
        saved = dict(id=8, input=INPUT, result=expected_result(INPUT))
        with TestClient(create_app(self.path)) as client:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                response = client.post('/api/v1/calculate', json=INPUT)
            self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
            self.assert_response(response, 200, saved['result'])
            self.assert_response(client.get('/api/v1/cases'), 200, [self.legacy])
            self.assert_old_snapshot_unchanged(7)
            self.assert_response(client.post('/api/v1/cases', json=INPUT), 201, saved)
            with patch('openoil.application.hydraulics.calculate',
                       side_effect=AssertionError('must not recalculate')):
                self.assert_response(client.get('/api/v1/cases/8'), 200, saved)
                self.assert_response(client.get('/api/v1/cases'), 200, [self.legacy, saved])
        self.assert_old_snapshot_unchanged(8)
        with TestClient(create_app(self.path)) as client:
            with patch('openoil.application.hydraulics.calculate',
                       side_effect=AssertionError('must not recalculate')):
                self.assert_response(client.get('/api/v1/cases/7'), 200, self.legacy)
                self.assert_response(client.get('/api/v1/cases/8'), 200, saved)
                self.assert_response(client.get('/api/v1/cases'), 200, [self.legacy, saved])
        self.assert_old_snapshot_unchanged(8)

    def test_rejection_categories_leave_records_and_next_id_unchanged(self):
        with TestClient(create_app(self.path), raise_server_exceptions=False) as client:
            baseline = [self.legacy]
            for body, message in [
                ({'input_schema_version': '1', 'input': INPUT}, 'invalid request body'),
                (None, 'invalid request body'),
                ([], 'invalid request body'),
                (dict(INPUT, sections=[]), 'sections must not be empty'),
                (dict(INPUT, flow_m3_s=.02), 'Reynolds number outside supported regimes'),
                (dict(INPUT, input_schema_version='2'), 'invalid request body'),
                (dict(INPUT, model_version='other'), 'invalid request body'),
                (dict(INPUT, density_kg_m3=0),
                 'density_kg_m3 must be a positive finite number'),
                (dict(INPUT, flow_m3_s='secret'), 'invalid request body'),
            ]:
                for route in ['/api/v1/calculate', '/api/v1/cases']:
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        self.assert_response(client.post(route, json=body), 422, {'detail': message})
                    self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                    self.assert_response(client.get('/api/v1/cases'), 200, baseline)
                    self.assert_old_snapshot_unchanged(7)
            for route in ['/api/v1/calculate', '/api/v1/cases']:
                for raw in ['{', '{"flow_m3_s":NaN}']:
                    self.assert_response(client.post(route, content=raw,
                                         headers={'content-type': 'application/json'}),
                                         422, {'detail': 'invalid request body'})
                    self.assert_response(client.get('/api/v1/cases'), 200, baseline)
                    self.assert_old_snapshot_unchanged(7)
            for value in ['0', '-1', 'abc', '9223372036854775808']:
                self.assert_response(client.get('/api/v1/cases/' + value), 422,
                                     {'detail': 'invalid case id'})
            self.assert_response(client.get('/api/v1/cases/8'), 404, {'detail': 'case not found'})
            for method, verb, route, kwargs in [
                ('save', 'post', '/api/v1/cases', {'json': INPUT}),
                ('list', 'get', '/api/v1/cases', {}),
                ('get', 'get', '/api/v1/cases/7', {}),
            ]:
                with patch('openoil.adapters.outbound.case_store.CaseStore.' + method,
                           side_effect=ValueError('private infrastructure detail')):
                    response = getattr(client, verb)(route, **kwargs)
                self.assertEqual((response.status_code, response.text), (500, 'Internal Server Error'))
                self.assert_response(client.get('/api/v1/cases'), 200, baseline)
                self.assert_old_snapshot_unchanged(7)
            # A serialization failure must not insert a partial snapshot either.
            with patch('openoil.application.hydraulics.provenance',
                       return_value={'invalid': float('nan')}):
                response = client.post('/api/v1/cases', json=INPUT)
            self.assertEqual((response.status_code, response.text), (500, 'Internal Server Error'))
            self.assert_response(client.get('/api/v1/cases'), 200, baseline)
            self.assert_old_snapshot_unchanged(7)
            saved = dict(id=8, input=INPUT, result=expected_result(INPUT))
            self.assert_response(client.post('/api/v1/cases', json=INPUT), 201, saved)
            self.assert_response(client.get('/api/v1/cases/8'), 200, saved)
            self.assert_old_snapshot_unchanged(8)
