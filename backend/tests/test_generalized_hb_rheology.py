"""Algebraic SI checks for the generalized parametric model, not vendor parity."""

import io
import math
import unittest
from contextlib import redirect_stderr, redirect_stdout

from openoil.domain import generalized_hb_rheology

PARAMETERS = {
    'reference_stress_pa': 10.0, 'zero_shear_stress_pa': 3.0,
    'high_shear_viscosity_pa_s': 0.2, 'stress_exponent': 2.0,
    'rate_exponent': 2.0, 'shear_rates_s_inv': [40.0, 0.0],
}


class GeneralizedHBRheologyTests(unittest.TestCase):
    def test_evaluates_documented_dimensionless_relation_and_provenance(self):
        original = dict(PARAMETERS, shear_rates_s_inv=list(PARAMETERS['shear_rates_s_inv']))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = generalized_hb_rheology.calculate(**PARAMETERS)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(PARAMETERS, original)
        self.assertEqual(result['curve'][0], {'shear_rate_s_inv': 0.0, 'shear_stress_pa': 3.0})
        self.assertAlmostEqual(result['curve'][1]['shear_stress_pa'], math.sqrt(73))
        self.assertEqual(result['parameters']['reference_stress_pa'], {'value': 10.0, 'unit': 'Pa'})
        self.assertEqual(result['parameters']['zero_shear_stress_pa'], {'value': 3.0, 'unit': 'Pa'})
        self.assertEqual(result['parameters']['high_shear_viscosity_pa_s'], {'value': 0.2, 'unit': 'Pa·s'})
        self.assertEqual(result['parameters']['stress_exponent'], {'value': 2.0, 'unit': '1'})
        self.assertEqual(result['parameters']['rate_exponent'], {'value': 2.0, 'unit': '1'})
        self.assertEqual(result['model_id'], 'openoil.rheology.generalized-herschel-bulkley-parametric')
        self.assertEqual(result['model_version'], '1.0.0')
        self.assertEqual(result['input_schema_version'], '1')
        self.assertEqual(result['result_schema_version'], '1')
        self.assertEqual(result['applicability']['status'], 'supported')
        self.assertIn('supplied', result['applicability']['assumptions'])
        self.assertIn('not validated for field decisions', result['applicability']['limitations'])

    def test_linear_limit_and_zero_viscosity(self):
        linear = generalized_hb_rheology.calculate(**dict(PARAMETERS, stress_exponent=1,
            rate_exponent=1, shear_rates_s_inv=[100]))
        self.assertAlmostEqual(linear['curve'][0]['shear_stress_pa'], 23.0)
        constant = generalized_hb_rheology.calculate(**dict(PARAMETERS,
            high_shear_viscosity_pa_s=0, shear_rates_s_inv=[0, 100]))
        self.assertEqual([point['shear_stress_pa'] for point in constant['curve']], [3, 3])

    def test_rejects_invalid_input_without_mutation(self):
        cases = [
            ('reference_stress_pa', 0, 'reference_stress_pa must be positive and finite'),
            ('reference_stress_pa', math.inf, 'reference_stress_pa must be positive and finite'),
            ('zero_shear_stress_pa', -1, 'zero_shear_stress_pa must be nonnegative and finite'),
            ('high_shear_viscosity_pa_s', math.nan, 'high_shear_viscosity_pa_s must be nonnegative and finite'),
            ('stress_exponent', 0, 'stress_exponent must be positive and finite'),
            ('rate_exponent', True, 'rate_exponent must be positive and finite'),
            ('shear_rates_s_inv', [], 'shear_rates_s_inv must not be empty'),
            ('shear_rates_s_inv', [0, 0], 'shear rates must be unique'),
            ('shear_rates_s_inv', [-1], 'shear rates must be nonnegative and finite'),
            ('shear_rates_s_inv', [math.inf], 'shear rates must be nonnegative and finite'),
        ]
        for name, value, message in cases:
            payload = dict(PARAMETERS, shear_rates_s_inv=list(PARAMETERS['shear_rates_s_inv']))
            payload[name] = value
            before = dict(payload)
            with self.subTest(name=name, value=value), self.assertRaises(ValueError) as caught:
                generalized_hb_rheology.calculate(**payload)
            self.assertEqual(str(caught.exception), message)
            self.assertEqual(payload, before)
        with self.assertRaisesRegex(ValueError, '^calculation outside finite numerical range$'):
            generalized_hb_rheology.calculate(**dict(PARAMETERS, stress_exponent=1,
                rate_exponent=2, shear_rates_s_inv=[1e308]))


if __name__ == '__main__':
    unittest.main()
