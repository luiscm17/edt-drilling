"""Versioned HTTP snapshots, including migration from the actual old schema."""
from contextlib import closing, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from wellplan_hydraulics.api import create_app
from test_api import INPUT, expected_result


BODY = {'input_schema_version': '1', 'input': INPUT}
ASSUMPTIONS = [
    'Steady incompressible single-phase Newtonian flow; constant properties.',
    'Concentric vertical well; zero surface annular gauge pressure.',
    'Laminar pipe 64/Re; exact concentric laminar annulus; smooth-wall Blasius '
    'with hydraulic diameter for turbulent annulus (approximation).',
    'Re < 2300 or 4000 <= Re <= 100000; pipe_OD/hole_ID <= 0.8.',
    'No bit/nozzle, surface, roughness, eccentricity, inclination, rotation, '
    'cuttings, thermal, compressibility, transient or swab/surge effects.',
    'Pipe friction is not standpipe pressure; not validated for field decisions.',
]


class VersionedCasesTests(unittest.TestCase):
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

    def provenance(self, response):
        value = response['provenance']
        from datetime import datetime
        self.assertEqual(datetime.fromisoformat(value['created_at']).utcoffset().total_seconds(), 0)
        self.assertEqual(value, dict(
            model_id='openoil.hydraulics.newtonian-concentric-vertical',
            model_version='1.0.0', units='SI', input_schema_version='1',
            result_schema_version='1', assumptions=ASSUMPTIONS,
            created_at=value['created_at']))
        return value

    def test_old_schema_restart_idempotence_bytes_and_no_recalculation(self):
        for _ in range(2):
            with TestClient(create_app(self.path)) as client:
                with patch('wellplan_hydraulics.application.calculate',
                           side_effect=AssertionError('must not recalculate')):
                    self.assert_response(client.get('/api/cases/7'), 200, self.legacy)
                    self.assert_response(client.get('/api/cases'), 200, [self.legacy])
                    old = dict(self.legacy, provenance=None)
                    self.assert_response(client.get('/api/v2/cases/7'), 200, old)
                    self.assert_response(client.get('/api/v2/cases'), 200, [old])
            with closing(sqlite3.connect(self.path)) as db:
                self.assertEqual(db.execute('SELECT input_json, result_json FROM cases').fetchall(),
                                 [(self.old_input, self.old_result)])
                self.assertEqual([r[1] for r in db.execute('PRAGMA table_info(cases)')],
                                 ['id', 'input_json', 'result_json', 'provenance_json'])
                self.assertEqual(db.execute('SELECT seq FROM sqlite_sequence WHERE name="cases"').fetchone(), (7,))

    def test_calculate_save_restart_and_v1_projection(self):
        with TestClient(create_app(self.path)) as client:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                response = client.post('/api/v2/calculate', json=BODY)
            self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
            calculated = response.json()
            self.provenance(calculated)
            self.assert_response(response, 200, dict(input=INPUT, result=expected_result(INPUT),
                                                   provenance=calculated['provenance']))
            self.assert_response(client.get('/api/cases'), 200, [self.legacy])
            response = client.post('/api/v2/cases', json=BODY)
            saved = response.json()
            self.provenance(saved)
            self.assert_response(response, 201, dict(calculated, id=8, provenance=saved['provenance']))
            v1 = {k: saved[k] for k in ('id', 'input', 'result')}
            self.assert_response(client.get('/api/cases/8'), 200, v1)
            # New v1 saves also retain truthful provenance, invisible to old clients.
            self.assert_response(client.post('/api/cases', json=INPUT), 201, dict(v1, id=9))
            self.provenance(client.get('/api/v2/cases/9').json())
        with TestClient(create_app(self.path)) as client:
            with patch('wellplan_hydraulics.application.calculate',
                       side_effect=AssertionError('must not recalculate')):
                self.assert_response(client.get('/api/v2/cases/8'), 200, saved)
                records = client.get('/api/v2/cases').json()
                self.assertEqual([r['id'] for r in records], [7, 8, 9])
                self.assertEqual(records[1], saved)

    def test_rejection_categories_leave_records_and_next_id_unchanged(self):
        with TestClient(create_app(self.path), raise_server_exceptions=False) as client:
            baseline = client.get('/api/v2/cases').json()
            for body, message in [
                (INPUT, 'invalid request body'),
                (None, 'invalid request body'),
                ([], 'invalid request body'),
                (dict(BODY, input=dict(INPUT, sections=[])), 'sections must not be empty'),
                (dict(BODY, input=dict(INPUT, flow_m3_s=.02)),
                 'Reynolds number outside supported regimes'),
                (dict(BODY, input_schema_version='2'), 'invalid request body'),
                (dict(BODY, model_version='other'), 'invalid request body'),
                (dict(BODY, input=dict(INPUT, density_kg_m3=0)),
                 'density_kg_m3 must be a positive finite number'),
                (dict(BODY, input=dict(INPUT, flow_m3_s='secret')), 'invalid request body'),
            ]:
                for route in ['/api/v2/calculate', '/api/v2/cases']:
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        self.assert_response(client.post(route, json=body), 422, {'detail': message})
                    self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                    self.assert_response(client.get('/api/v2/cases'), 200, baseline)
            for route in ['/api/v2/calculate', '/api/v2/cases']:
                for raw in ['{', '{"input_schema_version":"1","input":{"flow_m3_s":NaN}}']:
                    self.assert_response(client.post(route, content=raw,
                                         headers={'content-type': 'application/json'}),
                                         422, {'detail': 'invalid request body'})
                    self.assert_response(client.get('/api/v2/cases'), 200, baseline)
            for value in ['0', '-1', 'abc', '9223372036854775808']:
                self.assert_response(client.get('/api/v2/cases/' + value), 422,
                                     {'detail': 'invalid case id'})
            self.assert_response(client.get('/api/v2/cases/8'), 404, {'detail': 'case not found'})
            for method, verb, route, kwargs in [
                ('save', 'post', '/api/v2/cases', {'json': BODY}),
                ('list', 'get', '/api/v2/cases', {}),
                ('get', 'get', '/api/v2/cases/7', {}),
            ]:
                with patch('wellplan_hydraulics.storage.CaseStore.' + method,
                           side_effect=ValueError('private infrastructure detail')):
                    response = getattr(client, verb)(route, **kwargs)
                self.assertEqual((response.status_code, response.text), (500, 'Internal Server Error'))
                self.assert_response(client.get('/api/v2/cases'), 200, baseline)
            # A serialization failure must not insert a partial snapshot either.
            with patch('wellplan_hydraulics.application.provenance',
                       return_value={'invalid': float('nan')}):
                response = client.post('/api/v2/cases', json=BODY)
            self.assertEqual((response.status_code, response.text), (500, 'Internal Server Error'))
            self.assert_response(client.get('/api/v2/cases'), 200, baseline)
            self.assertEqual(client.post('/api/v2/cases', json=BODY).json()['id'], 8)
