"""Independent nozzle equation and calculate-only public HTTP contract."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from openoil.main import create_app


ROUTE = '/api/v1/nozzle-velocity/calculate'
INPUT = {'flow_m3_s': 0.02, 'total_nozzle_area_m2': 0.0004}
HYDRAULIC = {
    'sections': [{'length_m': 100, 'pipe_id_m': 0.08,
                  'pipe_od_m': 0.1, 'hole_id_m': 0.2}],
    'density_kg_m3': 1000, 'viscosity_pa_s': 0.1, 'flow_m3_s': 0.001,
}


class NozzleVelocityNumericalTests(unittest.TestCase):
    def test_independent_si_values_and_dynamic_scaling(self):
        from openoil.domain.nozzle_velocity import calculate
        # Literal API formula + exact conversions reduces to (2850/2849)*Q/A.
        for flow, area, expected in [(0.02, 0.0004, 142500 / 2849),
                                     (0.04, 0.0004, 285000 / 2849),
                                     (0.02, 0.0008, 71250 / 2849),
                                     (2, 1, 5700 / 2849)]:
            with self.subTest(flow=flow, area=area):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assertAlmostEqual(calculate(flow, area), expected)
                self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))

    def test_invalid_numbers_and_unrepresentable_results_are_silently_rejected(self):
        from openoil.domain.nozzle_velocity import calculate
        for index in (0, 1):
            for value in (True, False, float('nan'), float('inf'),
                          -float('inf'), 0, -0.1, '1', None):
                values = [0.02, 0.0004]
                values[index] = value
                with self.subTest(index=index, value=value):
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        with self.assertRaises(ValueError):
                            calculate(*values)
                    self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        for values in [(1e308, 1e-308), (5e-324, 1e308)]:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, '^calculation outside finite numerical range$'):
                    calculate(*values)


class NozzleVelocityApiTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = self.enterContext(TestClient(create_app(Path(temp.name) / 'cases.sqlite3')))
        self.first = self.client.post('/api/v1/cases', json=HYDRAULIC).json()

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json(), body)

    def request_silently(self, route=ROUTE, **kwargs):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(route, **kwargs)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        return response

    def assert_storage_unchanged(self):
        self.assert_response(self.client.get('/api/v1/cases'), 200, [self.first])

    def assert_next_id(self):
        self.assert_storage_unchanged()
        self.assertEqual(self.client.post('/api/v1/cases', json=HYDRAULIC).json()['id'], 2)

    def test_documented_api_unit_equation_through_si_http_inputs(self):
        # Hand calculation: 0.95 * 296 gpm / (2.96 * 1 in²) = 95 ft/s.
        # Exactly 95 * 0.3048 = 28.956 m/s; no model helper supplies this oracle.
        response = self.request_silently(json={
            'flow_m3_s': 296 * 0.003785411784 / 60,
            'total_nozzle_area_m2': 0.0254 ** 2,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(set(response.json()), {'velocity_m_s'})
        self.assertAlmostEqual(response.json()['velocity_m_s'], 28.956, places=10)
        self.assert_next_id()

    def test_dynamic_success_without_persistence_or_id_allocation(self):
        for flow, area, expected in [(0.02, 0.0004, 142500 / 2849),
                                     (0.04, 0.0004, 285000 / 2849),
                                     (0.02, 0.0008, 71250 / 2849),
                                     (2, 1, 5700 / 2849)]:
            with self.subTest(flow=flow, area=area):
                response = self.request_silently(json={
                    'flow_m3_s': flow, 'total_nozzle_area_m2': area})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers['content-type'], 'application/json')
                self.assertEqual(set(response.json()), {'velocity_m_s'})
                self.assertAlmostEqual(response.json()['velocity_m_s'], expected, places=10)
                self.assert_storage_unchanged()
        self.assert_next_id()

    def test_rejections_leave_snapshots_and_id_sequence_unchanged(self):
        invalid = []
        for key in INPUT:
            for value in (True, False, 0, -1, '0.02', None):
                invalid.append(dict(INPUT, **{key: value}))
            invalid.append({name: value for name, value in INPUT.items() if name != key})
        invalid.extend([{}, [], None, {'input': INPUT}, dict(INPUT, unknown=1)])
        for body in invalid:
            with self.subTest(body=body):
                self.assert_response(self.request_silently(json=body), 422,
                                     {'detail': 'invalid request body'})
                self.assert_storage_unchanged()
        for key in INPUT:
            for token in ('NaN', 'Infinity', '-Infinity', '1e999'):
                raw = json.dumps(INPUT).replace(json.dumps(INPUT[key]), token)
                with self.subTest(key=key, token=token):
                    self.assert_response(self.request_silently(content=raw,
                        headers={'content-type': 'application/json'}),
                        422, {'detail': 'invalid request body'})
                    self.assert_storage_unchanged()
        self.assert_response(self.request_silently(content='{',
            headers={'content-type': 'application/json'}),
            422, {'detail': 'invalid request body'})
        for flow, area in [(1e308, 1e-308), (5e-324, 1e308)]:
            self.assert_response(self.request_silently(json={
                'flow_m3_s': flow, 'total_nozzle_area_m2': area}),
                422, {'detail': 'calculation outside finite numerical range'})
            self.assert_storage_unchanged()
        self.assert_next_id()

    def test_existing_routes_reject_nozzle_shape_without_contract_changes(self):
        # All sibling POST contracts remain independent of the new shape.
        for route, body in (
            ('/api/v1/calculate', INPUT), ('/api/v1/cases', INPUT),
            ('/api/v1/calculate', {'input_schema_version': '1', 'input': INPUT}),
            ('/api/v1/cases', {'input_schema_version': '1', 'input': INPUT}),
            ('/api/v1/torque-drag/calculate', INPUT),
        ):
            with self.subTest(route=route):
                self.assert_response(self.request_silently(route, json=body),
                                     422, {'detail': 'invalid request body'})
                self.assert_storage_unchanged()
        self.assert_next_id()


if __name__ == '__main__':
    unittest.main()
