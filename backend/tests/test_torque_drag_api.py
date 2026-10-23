"""Calculate-only torque/drag HTTP contract; observe storage via public routes."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from openoil.main import create_app


ROUTE = '/api/v1/torque-drag/calculate'
INPUT = {
    'sections': [{'length_m': 10, 'pipe_od_m': 0.1, 'air_weight_n_m': 100}],
    'inclination_deg': 0, 'density_kg_m3': 0,
    'axial_friction_coefficient': 0.2, 'rotational_friction_coefficient': 0.3,
}
HYDRAULIC = {
    'sections': [{'length_m': 100, 'pipe_id_m': 0.08,
                  'pipe_od_m': 0.1, 'hole_id_m': 0.2}],
    'density_kg_m3': 1000, 'viscosity_pa_s': 0.1, 'flow_m3_s': 0.001,
}


class TorqueDragApiTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = self.enterContext(TestClient(create_app(Path(temp.name) / 'cases.sqlite3')))
        self.first = self.client.post('/api/v1/cases', json=HYDRAULIC).json()

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json(), body)

    def assert_stored_unchanged(self):
        self.assert_response(self.client.get('/api/v1/cases'), 200, [self.first])
        self.assertEqual(self.client.post('/api/v1/cases', json=HYDRAULIC).json()['id'], 2)

    def test_success_raw_result_is_silent_and_does_not_save_or_consume_id(self):
        # Independent vertical hand calculation: 100 N/m * 10 m; no wall contact.
        row = {'submerged_weight_n_m': 100, 'axial_gravity_n': 1000,
               'normal_force_n': 0, 'axial_friction_n': 0,
               'rotational_friction_n': 0, 'pickup_tension_n': 1000,
               'slackoff_tension_n': 1000, 'rotating_torque_nm': 0}
        expected = {'sections': [row], 'pickup_tension_n': 1000,
                    'slackoff_tension_n': 1000, 'rotating_torque_nm': 0}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assert_response(self.client.post(ROUTE, json=INPUT), 200, expected)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assert_stored_unchanged()

    def test_rejections_are_exact_silent_and_leave_storage_and_ids_unchanged(self):
        invalid = []
        for key, value, message in [
            ('sections', [], 'sections must not be empty'),
            ('inclination_deg', -1, 'inclination_deg must satisfy 0 <= angle < 90'),
            ('inclination_deg', 90, 'inclination_deg must satisfy 0 <= angle < 90'),
            ('density_kg_m3', -1, 'density_kg_m3 must be nonnegative'),
            ('axial_friction_coefficient', -1, 'axial_friction_coefficient must be nonnegative'),
            ('rotational_friction_coefficient', -1, 'rotational_friction_coefficient must be nonnegative'),
            ('density_kg_m3', 2000, 'submerged weight must be positive in every section'),
            ('inclination_deg', 89, 'slackoff tension must be nonnegative in every section'),
        ]:
            invalid.append((dict(INPUT, **{key: value}), message))
        for key in ['length_m', 'pipe_od_m', 'air_weight_n_m']:
            data = deepcopy(INPUT)
            data['sections'][0][key] = 0
            invalid.append((data, f'{key} must be positive'))
        data = deepcopy(INPUT)
        data['sections'][0]['pipe_od_m'] = 1e308
        invalid.append((data, 'calculation outside finite numerical range'))
        for key, value in [('density_kg_m3', True), ('inclination_deg', '0'),
                           ('unknown', 1), ('sections', [{}]),
                           ('sections', 'not a list')]:
            invalid.append((dict(INPUT, **{key: value}), 'invalid request body'))
        data = deepcopy(INPUT)
        del data['inclination_deg']
        invalid.extend((body, 'invalid request body') for body in [data, [], None,
                       {'input': INPUT}, dict(INPUT, input_schema_version='1')])
        data = deepcopy(INPUT)
        data['sections'][0]['unknown'] = 1
        invalid.append((data, 'invalid request body'))
        for body, message in invalid:
            with self.subTest(body=body):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assert_response(self.client.post(ROUTE, json=body),
                                         422, {'detail': message})
                self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                self.assert_response(self.client.get('/api/v1/cases'), 200, [self.first])
        raw_bodies = ['{']
        for value in ['NaN', 'Infinity', '-Infinity', '1e999']:
            raw_bodies.append(json.dumps(INPUT).replace('"inclination_deg": 0',
                                                       '"inclination_deg": ' + value))
        for raw in raw_bodies:
            with self.subTest(raw=raw):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assert_response(self.client.post(ROUTE, content=raw,
                        headers={'content-type': 'application/json'}),
                        422, {'detail': 'invalid request body'})
                self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                self.assert_response(self.client.get('/api/v1/cases'), 200, [self.first])
        self.assert_stored_unchanged()

    def test_existing_hydraulic_validation_rejects_new_shape_unchanged(self):
        for route, body in [('/api/v1/calculate', INPUT), ('/api/v1/cases', INPUT),
                            ('/api/v1/calculate', {'input_schema_version': '1', 'input': INPUT}),
                            ('/api/v1/cases', {'input_schema_version': '1', 'input': INPUT})]:
            with self.subTest(route=route):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assert_response(self.client.post(route, json=body),
                                         422, {'detail': 'invalid request body'})
                self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                self.assert_response(self.client.get('/api/v1/cases'), 200, [self.first])
        self.assert_stored_unchanged()


if __name__ == '__main__':
    unittest.main()
