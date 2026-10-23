"""Public HTTP contract; SQLite state is observed only via case routes."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from openoil.adapters.inbound.http.schemas import CalculationInput
from openoil.main import create_app
from openoil.domain.physics import Section, calculate


INPUT = {
    'sections': [{'length_m': 100, 'pipe_id_m': 0.08,
                  'pipe_od_m': 0.10, 'hole_id_m': 0.20}],
    'density_kg_m3': 1000, 'viscosity_pa_s': 0.1, 'flow_m3_s': 0.001,
}


def expected_result(data):
    result = asdict(calculate(
        [Section(**s) for s in data['sections']], data['density_kg_m3'],
        data['viscosity_pa_s'], data['flow_m3_s']))
    result['sections'] = list(result['sections'])
    return result


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'cases.sqlite3'
        self.client = self.enterContext(TestClient(create_app(self.path)))

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json(), body)

    def test_bit_nozzle_pressure_loss_is_separate_stateless_and_validated(self):
        data = {'density_kg_m3': 1198.2642731689612,
                'flow_m3_s': 296 * 0.003785411784 / 60,
                'total_nozzle_area_m2': 0.0254 ** 2}
        route = '/api/v1/bit-nozzle-pressure-loss/calculate'
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(route, json=data)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertAlmostEqual(body['pressure_loss']['value'], 556612.8, delta=2)
        self.assertEqual(body['pressure_loss']['unit'], 'Pa')
        self.assertEqual(body['pressure_loss']['quantity'], 'bit_nozzle_pressure_loss')
        self.assertEqual(body['model_version'], '1.0.0')
        self.assertEqual(body['coefficient']['value'], 0.95)
        self.assertEqual(body['applicability']['status'], 'supported')
        # The new payload must not acquire meaning on any existing route.
        for old_route in ['/api/v1/calculate', '/api/v1/cases',
                          '/api/v1/nozzle-velocity/calculate',
                          '/api/v1/torque-drag/calculate']:
            self.assert_response(self.client.post(old_route, json=data), 422,
                                 {'detail': 'invalid request body'})
        invalid = [{}, dict(data, extra=1), dict(data, density_kg_m3=True),
                   dict(data, flow_m3_s='1')]
        invalid += [dict(data, **{field: value}) for field in data for value in [0, -1]]
        for bad in invalid:
            self.assert_response(self.client.post(route, json=bad), 422,
                                 {'detail': 'invalid request body'})
        for field in data:
            for value in ['NaN', 'Infinity', '-Infinity']:
                raw = '{' + ','.join('"' + key + '":' + (value if key == field else str(number))
                                     for key, number in data.items()) + '}'
                self.assert_response(self.client.post(route, content=raw,
                                     headers={'content-type': 'application/json'}), 422,
                                     {'detail': 'invalid request body'})
        self.assert_response(self.client.post(route, json=dict(data, density_kg_m3=1e308)), 422,
                             {'detail': 'calculation outside finite numerical range'})
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assert_response(self.client.get('/api/v1/cases/1'), 200, record)
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)
        # The existing base calculation keeps its exact contract.
        self.assert_response(self.client.post('/api/v1/calculate', json=INPUT), 200, expected_result(INPUT))

    def test_calculate_matches_core_without_saving_or_output(self):
        original = deepcopy(INPUT)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assert_response(self.client.post('/api/v1/calculate', json=INPUT),
                                 200, expected_result(INPUT))
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(INPUT, original)
        self.assert_response(self.client.get('/api/v1/cases'), 200, [])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 1)

    def test_saved_case_round_trip_and_persistence(self):
        record = {'id': 1, 'input': INPUT, 'result': expected_result(INPUT)}
        self.assert_response(self.client.post('/api/v1/cases', json=INPUT), 201, record)
        self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assert_response(self.client.get('/api/v1/cases/1'), 200, record)
        # A new app/connection must see the committed record.
        with TestClient(create_app(self.path)) as restarted:
            self.assert_response(restarted.get('/api/v1/cases/1'), 200, record)
            second = dict(record, id=2)
            self.assert_response(restarted.post('/api/v1/cases', json=INPUT), 201, second)
            self.assert_response(restarted.get('/api/v1/cases'), 200, [record, second])

    def test_rejected_inputs_leave_rows_and_ids_unchanged_and_are_silent(self):
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        invalid = []
        for key, value in [('density_kg_m3', 0), ('viscosity_pa_s', -1),
                           ('flow_m3_s', 0), ('sections', [])]:
            data = deepcopy(INPUT)
            data[key] = value
            message = ('sections must not be empty' if key == 'sections'
                       else f'{key} must be a positive finite number')
            invalid.append((data, message))
        for patch, message in [
            ({'pipe_id_m': 0.1}, 'geometry requires pipe_id_m < pipe_od_m < hole_id_m'),
            ({'pipe_od_m': 0.17}, 'annular diameter ratio must be <= 0.8'),
        ]:
            data = deepcopy(INPUT)
            data['sections'][0].update(patch)
            invalid.append((data, message))
        data = deepcopy(INPUT)
        data['flow_m3_s'] = 0.02
        invalid.append((data, 'Reynolds number outside supported regimes'))
        data = deepcopy(INPUT)
        data['sections'][0]['length_m'] = 1e308
        invalid.append((data, 'calculation outside finite numerical range'))
        for key, value in [('density_kg_m3', True), ('flow_m3_s', '0.001'),
                           ('unknown', 1), ('sections', [{}])]:
            data = deepcopy(INPUT)
            data[key] = value
            invalid.append((data, 'invalid request body'))
        data = deepcopy(INPUT)
        del data['density_kg_m3']
        invalid.extend([(data, 'invalid request body'), ([], 'invalid request body'),
                        (None, 'invalid request body')])
        for route in ['/api/v1/calculate', '/api/v1/cases']:
            for data, message in invalid:
                with self.subTest(route=route, data=data):
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        self.assert_response(self.client.post(route, json=data),
                                             422, {'detail': message})
                    self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                    self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
            for raw in ['{', '{"density_kg_m3": NaN}', '{"flow_m3_s": Infinity}']:
                self.assert_response(self.client.post(route, content=raw,
                                     headers={'content-type': 'application/json'}),
                                     422, {'detail': 'invalid request body'})
                self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)

    def test_load_and_list_do_not_recalculate_saved_snapshots(self):
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        with patch('openoil.application.hydraulics.calculate',
                   side_effect=AssertionError('must not recalculate')):
            self.assert_response(self.client.get('/api/v1/cases/1'), 200, record)
            self.assert_response(self.client.get('/api/v1/cases'), 200, [record])

    def test_existing_input_result_helper_is_preserved(self):
        data = CalculationInput(**INPUT)
        expected = expected_result(INPUT)
        expected['sections'] = tuple(expected['sections'])
        self.assertEqual(data.result(), expected)
        with self.assertRaises(HTTPException) as caught:
            CalculationInput(**dict(INPUT, density_kg_m3=0)).result()
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(caught.exception.detail,
                         'density_kg_m3 must be a positive finite number')

    def test_repository_errors_remain_server_errors_not_input_errors(self):
        with TestClient(create_app(self.path), raise_server_exceptions=False) as client:
            for method, verb, route, kwargs in [
                ('save', 'post', '/api/v1/cases', {'json': INPUT}),
                ('list', 'get', '/api/v1/cases', {}),
                ('get', 'get', '/api/v1/cases/1', {}),
            ]:
                with self.subTest(method=method):
                    with patch('openoil.adapters.outbound.case_store.CaseStore.' + method,
                               side_effect=ValueError('private infrastructure detail')):
                        response = getattr(client, verb)(route, **kwargs)
                    self.assertEqual(response.status_code, 500)
                    self.assertEqual(response.text, 'Internal Server Error')
        self.assert_response(self.client.get('/api/v1/cases'), 200, [])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 1)

    def test_missing_and_invalid_case_id_are_stable(self):
        self.assert_response(self.client.get('/api/v1/cases/1'), 404,
                             {'detail': 'case not found'})
        for value in ['0', '-1', 'abc', '9223372036854775808']:
            # Malformed-path migration belongs with the T5b error-handler fix.
            self.assert_response(self.client.get('/api/cases/' + value), 422,
                                 {'detail': 'invalid case id'})
        self.assert_response(self.client.get('/api/v1/cases'), 200, [])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 1)

    def test_v1_still_rejects_versioned_envelopes_without_saving(self):
        first = self.client.post('/api/v1/cases', json=INPUT).json()
        body = {'input_schema_version': '1', 'input': INPUT}
        for route in ['/api/v1/calculate', '/api/v1/cases']:
            self.assert_response(self.client.post(route, json=body), 422,
                                 {'detail': 'invalid request body'})
            self.assert_response(self.client.get('/api/v1/cases'), 200, [first])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)

    def test_preserves_multisection_and_turbulent_core_behavior(self):
        for flow in [0.001, 0.03]:
            data = deepcopy(INPUT)
            data['flow_m3_s'] = flow
            data['sections'] *= 2
            self.assert_response(self.client.post('/api/v1/calculate', json=data),
                                 200, expected_result(data))


if __name__ == '__main__':
    unittest.main()
