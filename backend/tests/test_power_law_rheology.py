"""Public-domain SI arithmetic from the documented Fann conversion, not vendor parity."""

import io
import math
import unittest
from contextlib import redirect_stderr, redirect_stdout

from openoil.domain import power_law_rheology


class PowerLawRheologyTests(unittest.TestCase):
    def test_two_point_si_curve_and_independent_observations(self):
        reading = power_law_rheology.FannReading
        values = [reading(600, 75), reading(300, 50), reading(100, 20)]
        original = list(values)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = power_law_rheology.calculate(values)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(values, original)
        self.assertEqual([p['rpm'] for p in result['readings']], [100, 300, 600])
        self.assertAlmostEqual(result['readings'][0]['shear_rate_s_inv'], 170.333)
        self.assertAlmostEqual(result['readings'][1]['shear_stress_pa'], 25.49623790702883)
        self.assertAlmostEqual(result['flow_behavior_index']['value'], 0.5849625007211562)
        self.assertEqual(result['flow_behavior_index']['unit'], '1')
        self.assertAlmostEqual(result['consistency_index']['value'], 0.6639753206166239)
        self.assertEqual(result['consistency_index']['unit'], 'Pa·s^n')
        self.assertEqual([p['rpm'] for p in result['model_curve']], [100, 300, 600])
        self.assertAlmostEqual(result['model_curve'][-1]['shear_stress_pa'], 38.244356860543256)
        self.assertEqual(result['model_id'], 'openoil.rheology.fann-power-law')
        self.assertEqual(result['model_version'], '1.0.0')
        self.assertEqual(result['input_schema_version'], '1')
        self.assertEqual(result['result_schema_version'], '1')
        self.assertEqual(result['applicability']['status'], 'supported')
        self.assertIn('300 and 600 rpm', result['applicability']['assumptions'])
        self.assertIn('not validated for field decisions', result['applicability']['limitations'])

    def test_rejects_invalid_pairs_without_mutating_readings(self):
        reading = power_law_rheology.FannReading
        cases = [
            ([], 'readings must contain at least 300 and 600 rpm'),
            ([reading(300, 50)], 'readings must contain at least 300 and 600 rpm'),
            ([reading(300, 50), reading(300, 75)], 'rpm readings must be unique'),
            ([reading(300, 50), reading(500, 75)], 'readings must include 300 and 600 rpm'),
            ([reading(300, 0), reading(600, 75)], '300 and 600 rpm dials must be positive'),
            ([reading(300, 50), reading(600, 0)], '300 and 600 rpm dials must be positive'),
            ([reading(300, 50), reading(600, 50)], '600 rpm dial must exceed 300 rpm dial'),
            ([reading(300, 50), reading(600, 40)], '600 rpm dial must exceed 300 rpm dial'),
            ([reading(300, 50), reading(600, 75), reading(100, -1)], 'dial must be nonnegative and finite'),
            ([reading(300, 50), reading(600, 75), reading(math.inf, 10)], 'rpm must be positive and finite'),
            ([reading(300, 50), reading(600, 75), reading(100, math.nan)], 'dial must be nonnegative and finite'),
            ([reading(300, 50), reading(600, 75), reading(True, 10)], 'rpm must be positive and finite'),
            ([reading(300, 50), reading(600, 75), reading(100, True)], 'dial must be nonnegative and finite'),
            ([reading(300, 50), reading(600, 75), reading(1.5e308, 1)], 'calculation outside finite numerical range'),
        ]
        for values, message in cases:
            original = list(values)
            with self.subTest(message=message, values=values):
                with self.assertRaises(ValueError) as caught:
                    power_law_rheology.calculate(values)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(values, original)


if __name__ == '__main__':
    unittest.main()
