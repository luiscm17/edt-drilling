import io
import unittest
from contextlib import redirect_stdout, redirect_stderr

from openoil.domain import newtonian_rheology as model
from openoil.domain.bingham_rheology import FannReading


class NewtonianTests(unittest.TestCase):
    def test_si_derivation_sorted_observations_and_zero(self):
        readings = [FannReading(600, 60), FannReading(100, 10)]
        original = list(readings)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = model.calculate(readings)
        self.assertAlmostEqual(result['dynamic_viscosity']['value'],
                               10 * 0.01065 * 47.88025898033584 / (100 * 1.70333))
        self.assertEqual(result['dynamic_viscosity']['unit'], 'Pa·s')
        self.assertEqual([p['rpm'] for p in result['readings']], [100, 600])
        self.assertEqual(result['readings'][0]['shear_rate_s_inv'], 170.333)
        self.assertAlmostEqual(result['readings'][0]['shear_stress_pa'], 5.099247581405767)
        self.assertEqual(model.calculate([FannReading(20, 0)])['dynamic_viscosity']['value'], 0)
        self.assertEqual(readings, original)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))

    def test_rejects_inconsistent_duplicate_invalid_and_unrepresentable_values(self):
        cases = [([], 'readings must not be empty'),
                 ([FannReading(10, 1), FannReading(10, 1)], 'rpm readings must be unique'),
                 ([FannReading(300, 50), FannReading(600, 75)], 'readings are inconsistent with a Newtonian model'),
                 ([FannReading(10, 0), FannReading(20, 1)], 'readings are inconsistent with a Newtonian model'),
                 ([FannReading(1.7e308, 1)], 'calculation outside finite numerical range'),
                 ([FannReading(10**400, 1)], 'rpm must be positive and finite'),
                 ([FannReading(10, 10**400)], 'dial must be nonnegative and finite'),
                 ([FannReading(1e-320, 1)], 'calculation outside finite numerical range'),
                 ([FannReading(10, 5e-324)], 'calculation outside finite numerical range')]
        for value in [0, -1, True, '2', float('nan'), float('inf')]:
            cases.append(([FannReading(value, 1)], 'rpm must be positive and finite'))
        for value in [-1, True, '2', float('nan'), float('inf')]:
            cases.append(([FannReading(10, value)], 'dial must be nonnegative and finite'))
        for readings, message in cases:
            original = list(readings)
            out, err = io.StringIO(), io.StringIO()
            with self.subTest(readings=readings), redirect_stdout(out), redirect_stderr(err):
                with self.assertRaisesRegex(ValueError, '^' + message + '$'):
                    model.calculate(readings)
            self.assertEqual(readings, original)
            self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))

    def test_only_floating_point_roundoff_tolerance_not_a_fluid_fit(self):
        result = model.calculate([FannReading(100, 10), FannReading(200, 20 * (1 + 5e-10))])
        self.assertGreater(result['dynamic_viscosity']['value'], 0)
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            model.calculate([FannReading(100, 10), FannReading(200, 20.000001)])
