"""Independent gel study contract, observed through its public HTTP interface."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from openoil.main import create_app


ROUTE = '/api/v1/rheology/gel-break-pressure/calculate'
DATA = {'dial_3_rpm': 10, 'components': [
    {'length_m': 100, 'inner_diameter_m': 0.1},
    {'length_m': 50, 'inner_diameter_m': 0.05},
]}
CASE = {'sections': [{'length_m': 100, 'pipe_id_m': 0.08,
                     'pipe_od_m': 0.1, 'hole_id_m': 0.2}],
        'density_kg_m3': 1000, 'viscosity_pa_s': 0.1, 'flow_m3_s': 0.001}


class GelBreakPressureTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = self.enterContext(TestClient(create_app(Path(temp.name) / 'cases.db')))
        self.record = self.client.post('/api/v1/cases', json=CASE).json()

    def post(self, data, status=200, detail=None):
        original = deepcopy(data)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            response = self.client.post(ROUTE, json=data)
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(data, original)
        if detail:
            self.assertEqual(response.json(), {'detail': detail})
        self.assertEqual(self.client.get('/api/v1/cases').json(), [self.record])
        self.assertEqual(self.client.get('/api/v1/cases/1').json(), self.record)
        return response.json()

    def assert_next_id(self):
        self.assertEqual(self.client.post('/api/v1/cases', json=CASE).json()['id'], 2)

    def test_zero_second_conversion_identifies_source_model_units_and_boundary(self):
        body = self.post(DATA)
        self.assertEqual(body['gel_stress']['quantity'], 'zero_second_gel_stress')
        self.assertEqual(body['gel_stress']['unit'], 'Pa')
        self.assertAlmostEqual(body['gel_stress']['value'], 5.099247581405767)
        self.assertEqual(body['source'], {'rpm': 3, 'dial': 10,
                         'stress_lb_ft2_per_dial': 0.01065,
                         'lb_ft2_to_pa': 47.88025898033584})
        self.assertEqual(body['model_id'], 'openoil.rheology.fann-zero-second-gel-break-pressure')
        self.assertEqual([body[key] for key in ['model_version', 'input_schema_version',
                                                'result_schema_version']], ['1.0.0', '1', '1'])
        self.assertEqual(body['scope'], 'string interior only')
        self.assertEqual(body['applicability']['status'], 'supported')
        for excluded in ['annulus', 'timed gels', 'tool joints', 'WellPlan parity',
                         'Herschel–Bulkley', 'field decisions']:
            self.assertIn(excluded, body['applicability']['limitations'])
        self.assert_next_id()

    def test_pressure_equation_ordered_component_breakdown_and_zero_boundary(self):
        body = self.post(DATA)
        self.assertEqual(body['pressure']['unit'], 'Pa')
        self.assertEqual(body['pressure']['quantity'], 'interior_break_gel_pressure')
        self.assertAlmostEqual(body['pressure']['value'], 40793.98065124614)
        self.assertEqual(len(body['components']), 2)
        for source, result in zip(DATA['components'], body['components']):
            self.assertEqual(result, dict(source, pressure_pa=body['pressure']['value'] / 2))
        zero = self.post(dict(DATA, dial_3_rpm=0))
        self.assertEqual(zero['gel_stress']['value'], 0)
        self.assertEqual(zero['pressure']['value'], 0)
        self.assertEqual([c['pressure_pa'] for c in zero['components']], [0, 0])
        self.assert_next_id()

    def test_dial_requires_finite_nonnegative_strict_number(self):
        for value in [-1, True, '10', None]:
            self.post(dict(DATA, dial_3_rpm=value), 422, 'invalid request body')
        for value in ['NaN', 'Infinity', '-Infinity']:
            raw = '{"dial_3_rpm":' + value + ',"components":[{"length_m":1,"inner_diameter_m":1}]}'
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                response = self.client.post(ROUTE, content=raw,
                                            headers={'content-type': 'application/json'})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {'detail': 'invalid request body'})
            self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
            self.assertEqual(self.client.get('/api/v1/cases').json(), [self.record])
        self.assert_next_id()

    def test_geometry_requires_nonempty_positive_finite_strict_components(self):
        for data in [{}, dict(DATA, components=[]), dict(DATA, extra=1),
                     dict(DATA, components=[{}]), dict(DATA, components=[dict(DATA['components'][0], extra=1)])]:
            self.post(data, 422, 'invalid request body')
        for field in ['length_m', 'inner_diameter_m']:
            for value in [0, -1, True, '1', None]:
                component = dict(DATA['components'][0], **{field: value})
                self.post(dict(DATA, components=[component]), 422, 'invalid request body')
            for value in ['NaN', 'Infinity', '-Infinity']:
                raw = ('{"dial_3_rpm":10,"components":[{"length_m":1,"inner_diameter_m":1}]}').replace(
                    '"' + field + '":1', '"' + field + '":' + value)
                response = self.client.post(ROUTE, content=raw, headers={'content-type': 'application/json'})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json(), {'detail': 'invalid request body'})
                self.assertEqual(self.client.get('/api/v1/cases').json(), [self.record])
        self.assert_next_id()

    def test_nonfinite_component_and_total_results_are_rejected(self):
        for data in [dict(DATA, components=[{'length_m': 1e308, 'inner_diameter_m': 1e-308}]),
                     dict(DATA, dial_3_rpm=1e308),
                     {'dial_3_rpm': 1, 'components': [
                         {'length_m': 5e307, 'inner_diameter_m': 1}] * 2},
                     dict(DATA, dial_3_rpm=0, components=[
                         {'length_m': 1e308, 'inner_diameter_m': 1e-308}])]:
            self.post(data, 422, 'calculation outside finite numerical range')
        self.assert_next_id()

    def test_openapi_help_exposes_units_and_interior_only_scope(self):
        operation = self.client.get('/openapi.json').json()['paths'][ROUTE]['post']
        self.assertIn('interior', operation['description'])
        self.assertIn('Pa', operation['description'])
        self.assertIn('3 rpm', operation['description'])
        self.assert_next_id()


if __name__ == '__main__':
    unittest.main()
