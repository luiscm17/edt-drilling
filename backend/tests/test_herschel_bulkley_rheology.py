"""Algebraic checks for the conventional Herschel-Bulkley parametric model."""

import math
import unittest

from openoil.domain import herschel_bulkley_rheology


class HerschelBulkleyRheologyTests(unittest.TestCase):
    def test_evaluates_curve_and_reports_model_parameters(self):
        result = herschel_bulkley_rheology.calculate(
            yield_stress_pa=3, consistency_index_pa_s_n=0.2,
            flow_behavior_index=1, shear_rates_s_inv=[40, 0],
        )
        self.assertEqual(result['curve'], [
            {'shear_rate_s_inv': 0, 'shear_stress_pa': 3},
            {'shear_rate_s_inv': 40, 'shear_stress_pa': 11},
        ])
        self.assertEqual(result['parameters']['yield_stress_pa'], {'value': 3, 'unit': 'Pa'})
        self.assertEqual(result['parameters']['consistency_index_pa_s_n'],
                         {'value': 0.2, 'unit': 'Pa·s^n'})
        self.assertEqual(result['parameters']['flow_behavior_index'], {'value': 1, 'unit': '1'})
        self.assertEqual(result['model_id'], 'openoil.rheology.herschel-bulkley-parametric')
        self.assertEqual(result['model_version'], '1.0.0')
        self.assertEqual(result['input_schema_version'], '1')
        self.assertEqual(result['result_schema_version'], '1')
        self.assertEqual(result['applicability']['status'], 'supported')
        self.assertIn('No Fann fit', result['applicability']['limitations'])

    def test_bingham_and_power_law_special_cases(self):
        bingham = herschel_bulkley_rheology.calculate(
            yield_stress_pa=3, consistency_index_pa_s_n=0.2,
            flow_behavior_index=1, shear_rates_s_inv=[10],
        )
        power_law = herschel_bulkley_rheology.calculate(
            yield_stress_pa=0, consistency_index_pa_s_n=0.2,
            flow_behavior_index=2, shear_rates_s_inv=[10],
        )
        self.assertAlmostEqual(bingham['curve'][0]['shear_stress_pa'], 5)
        self.assertEqual(power_law['curve'][0]['shear_stress_pa'], 20)

    def test_rejects_invalid_parameters_rates_and_unrepresentable_output(self):
        base = dict(yield_stress_pa=3, consistency_index_pa_s_n=0.2,
                    flow_behavior_index=0.5, shear_rates_s_inv=[0, 40])
        invalid = [
            dict(base, yield_stress_pa=-1), dict(base, consistency_index_pa_s_n=-1),
            dict(base, flow_behavior_index=0), dict(base, flow_behavior_index=math.inf),
            dict(base, shear_rates_s_inv=[]), dict(base, shear_rates_s_inv=[0, 0]),
            dict(base, shear_rates_s_inv=[-1]), dict(base, shear_rates_s_inv=[math.nan]),
        ]
        for payload in invalid:
            with self.subTest(keys=tuple(payload)), self.assertRaises(ValueError):
                herschel_bulkley_rheology.calculate(**payload)
        with self.assertRaises(ValueError):
            herschel_bulkley_rheology.calculate(**dict(base, yield_stress_pa=10**400))
        with self.assertRaisesRegex(ValueError, '^calculation outside finite numerical range$'):
            herschel_bulkley_rheology.calculate(
                yield_stress_pa=0, consistency_index_pa_s_n=1e308,
                flow_behavior_index=2, shear_rates_s_inv=[1e308],
            )


if __name__ == '__main__':
    unittest.main()
