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
            self.assert_response(self.client.get('/api/v1/cases/' + value), 422,
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


    def test_herschel_bulkley_study_is_stateless_and_strict(self):
        route = '/api/v1/rheology/herschel-bulkley/calculate'
        data = {'yield_stress_pa': 3, 'consistency_index_pa_s_n': 0.2,
                'flow_behavior_index': 1, 'shear_rates_s_inv': [40, 0]}
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(route, json=data)
            for sibling in ['/api/v1/calculate', '/api/v1/cases',
                            '/api/v1/rheology/bingham/calculate',
                            '/api/v1/rheology/power-law/calculate',
                            '/api/v1/rheology/generalized-hb/calculate']:
                rejected = self.client.post(sibling, json=data)
                self.assert_response(rejected, 422, {'detail': 'invalid request body'})
            for invalid in [dict(data, extra=1), dict(data, flow_behavior_index=True),
                            dict(data, shear_rates_s_inv=[0, 0])]:
                rejected = self.client.post(route, json=invalid)
                self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['model_id'], 'openoil.rheology.herschel-bulkley-parametric')
        self.assertEqual(body['parameters']['yield_stress_pa'], {'value': 3, 'unit': 'Pa'})
        self.assertEqual(body['parameters']['consistency_index_pa_s_n'],
                         {'value': 0.2, 'unit': 'Pa·s^n'})
        self.assertEqual(body['parameters']['flow_behavior_index'], {'value': 1, 'unit': '1'})
        self.assertEqual(body['curve'], [
            {'shear_rate_s_inv': 0, 'shear_stress_pa': 3},
            {'shear_rate_s_inv': 40, 'shear_stress_pa': 11},
        ])
        for _ in range(4):
            self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)

    def test_generalized_hb_parametric_study_is_stateless_and_strict(self):
        route = '/api/v1/rheology/generalized-hb/calculate'
        data = {'reference_stress_pa': 10, 'zero_shear_stress_pa': 3,
                'high_shear_viscosity_pa_s': 0.2, 'stress_exponent': 2,
                'rate_exponent': 2, 'shear_rates_s_inv': [40, 0]}
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(route, json=data)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(set(body), {'parameters', 'curve', 'model_id', 'model_version',
                                     'input_schema_version', 'result_schema_version', 'applicability'})
        self.assertEqual(body['model_id'], 'openoil.rheology.generalized-herschel-bulkley-parametric')
        self.assertEqual(body['curve'][0], {'shear_rate_s_inv': 0, 'shear_stress_pa': 3})
        self.assertAlmostEqual(body['curve'][1]['shear_stress_pa'], 73 ** 0.5)
        self.assertEqual(body['parameters']['reference_stress_pa'], {'value': 10, 'unit': 'Pa'})
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        for old_route in ['/api/v1/calculate', '/api/v1/cases',
                          '/api/v1/rheology/power-law/calculate',
                          '/api/v1/rheology/bingham/calculate']:
            self.assert_response(self.client.post(old_route, json=data), 422,
                                 {'detail': 'invalid request body'})
        for invalid, detail in [
            ({}, 'invalid request body'),
            (dict(data, extra=1), 'invalid request body'),
            (dict(data, stress_exponent=True), 'invalid request body'),
            (dict(data, shear_rates_s_inv=[]), 'invalid request body'),
            (dict(data, stress_exponent=0), 'invalid request body'),
            (dict(data, shear_rates_s_inv=[0, 0]), 'shear rates must be unique'),
        ]:
            self.assert_response(self.client.post(route, json=invalid), 422,
                                 {'detail': detail})
            self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)

    def test_power_law_study_is_strict_stateless_and_isolated_from_existing_routes(self):
        route = '/api/v1/rheology/power-law/calculate'
        data = {'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 600, 'dial': 75},
                             {'rpm': 100, 'dial': 20}]}
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(route, json=data)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(set(result), {'readings', 'model_curve', 'flow_behavior_index',
                                       'consistency_index', 'model_id', 'model_version',
                                       'input_schema_version', 'result_schema_version',
                                       'applicability'})
        self.assertEqual(result['model_id'], 'openoil.rheology.fann-power-law')
        self.assertAlmostEqual(result['flow_behavior_index']['value'], 0.5849625007211562)
        self.assertAlmostEqual(result['consistency_index']['value'], 0.6639753206166239)
        self.assertEqual(result['consistency_index']['unit'], 'Pa·s^n')
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        zero_observation = {'readings': [*data['readings'][:2], {'rpm': 100, 'dial': 0}]}
        zero_result = self.client.post(route, json=zero_observation)
        self.assertEqual(zero_result.status_code, 200, zero_result.text)
        self.assertEqual(zero_result.json()['readings'][0]['shear_stress_pa'], 0)
        self.assertGreater(zero_result.json()['model_curve'][0]['shear_stress_pa'], 0)
        self.assertAlmostEqual(zero_result.json()['flow_behavior_index']['value'],
                               result['flow_behavior_index']['value'])
        for old_route in ['/api/v1/calculate', '/api/v1/cases',
                          '/api/v1/bit-nozzle-pressure-loss/calculate']:
            self.assert_response(self.client.post(old_route, json=data), 422,
                                 {'detail': 'invalid request body'})
        bingham = self.client.post('/api/v1/rheology/bingham/calculate', json=data)
        self.assertEqual(bingham.status_code, 200, bingham.text)
        self.assertEqual(bingham.json()['model_id'], 'openoil.rheology.fann-bingham')
        for invalid, expected in [
            ({}, 'invalid request body'),
            (dict(data, unknown=1), 'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': True}, {'rpm': 600, 'dial': 75}]}, 'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': 0}, {'rpm': 600, 'dial': 75}]},
             '300 and 600 rpm dials must be positive'),
            ({'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 600, 'dial': 50}]},
             '600 rpm dial must exceed 300 rpm dial'),
        ]:
            with self.subTest(invalid=invalid):
                self.assert_response(self.client.post(route, json=invalid), 422,
                                     {'detail': expected})
                self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assert_response(self.client.get('/api/v1/cases'), 200, [record])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)

    def test_bingham_rheology_is_stateless_strict_and_does_not_change_sibling_routes(self):
        route = '/api/v1/rheology/bingham/calculate'
        data = {'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 600, 'dial': 75},
                             {'rpm': 100, 'dial': 25}]}
        record = self.client.post('/api/v1/cases', json=INPUT).json()
        stress_pa_per_dial = 0.01065 * 47.88025898033584
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            response = self.client.post(route, json=data)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['model_id'], 'openoil.rheology.fann-bingham')
        self.assertEqual(body['model_version'], '1.0.0')
        self.assertEqual(body['input_schema_version'], '1')
        self.assertEqual(body['result_schema_version'], '1')
        self.assertEqual(body['plastic_viscosity']['quantity'], 'plastic_viscosity')
        self.assertEqual(body['plastic_viscosity']['unit'], 'Pa·s')
        self.assertAlmostEqual(body['plastic_viscosity']['value'],
                               25 * stress_pa_per_dial / (1.70333 * 300))
        self.assertEqual(body['yield_point']['quantity'], 'yield_point')
        self.assertEqual(body['yield_point']['unit'], 'Pa')
        self.assertAlmostEqual(body['yield_point']['value'], 25 * stress_pa_per_dial)
        self.assertEqual([point['rpm'] for point in body['readings']], [100, 300, 600])
        self.assertEqual(body['applicability']['status'], 'supported')
        self.assertEqual(self.client.get('/api/v1/cases').json(), [record])
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ('', ''))

        invalid = [
            ({}, 'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 600}]}, 'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': 50, 'extra': 1}, {'rpm': 600, 'dial': 75}]},
             'invalid request body'),
            ({'readings': [{'rpm': True, 'dial': 50}, {'rpm': 600, 'dial': 75}]},
             'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': '50'}, {'rpm': 600, 'dial': 75}]},
             'invalid request body'),
            ({'readings': [{'rpm': 0, 'dial': 50}, {'rpm': 600, 'dial': 75}]},
             'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': -1}, {'rpm': 600, 'dial': 75}]},
             'invalid request body'),
            ({'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 300, 'dial': 60}]},
             'rpm readings must be unique'),
            ({'readings': [{'rpm': 300, 'dial': 50}, {'rpm': 400, 'dial': 60}]},
             'readings must include 300 and 600 rpm'),
            ({'readings': [{'rpm': 300, 'dial': 60}, {'rpm': 600, 'dial': 50}]},
             'derived plastic viscosity must be nonnegative'),
            ({'readings': [{'rpm': 300, 'dial': 30}, {'rpm': 600, 'dial': 70}]},
             'derived yield point must be nonnegative'),
        ]
        for bad, detail in invalid:
            with self.subTest(data=bad, detail=detail):
                self.assert_response(self.client.post(route, json=bad), 422, {'detail': detail})
                self.assertEqual(self.client.get('/api/v1/cases').json(), [record])
        raw = '{"readings":[{"rpm":300,"dial":50},{"rpm":600,"dial":NaN}]}'
        self.assert_response(self.client.post(route, content=raw,
                             headers={'content-type': 'application/json'}),
                             422, {'detail': 'invalid request body'})
        for sibling in ['/api/v1/calculate', '/api/v1/cases',
                        '/api/v1/nozzle-velocity/calculate', '/api/v1/torque-drag/calculate']:
            with self.subTest(sibling=sibling):
                self.assert_response(self.client.post(sibling, json=data), 422,
                                     {'detail': 'invalid request body'})
                self.assertEqual(self.client.get('/api/v1/cases').json(), [record])
        self.assertEqual(self.client.post('/api/v1/cases', json=INPUT).json()['id'], 2)


if __name__ == '__main__':
    unittest.main()
