"""Independent arithmetic and numerical boundaries through the pure public interface."""
from copy import deepcopy
from math import isfinite
import unittest

from openoil.domain.bingham_rheology import FannReading
from openoil.domain.herschel_bulkley_fit import calculate


class FitTests(unittest.TestCase):
    def test_hand_check_square_root_and_order_independence(self):
        # gamma = 1,4,9; stress = 2 + 3*sqrt(gamma), exactly 5,8,11 Pa.
        readings = [FannReading(g / 1.70333, t / (0.01065 * 47.88025898033584))
                    for g, t in [(9, 11), (1, 5), (4, 8)]]
        original = deepcopy(readings)
        result = calculate(readings)
        self.assertEqual(readings, original)
        self.assertEqual(result, calculate(readings[::-1]))
        for key, expected in [('yield_stress_pa', 2), ('consistency_index_pa_s_n', 3),
                              ('flow_behavior_index', 0.5)]:
            self.assertAlmostEqual(result['parameters'][key]['value'], expected, places=10)
        self.assertEqual([p['shear_rate_s_inv'] for p in result['points']], [1, 4, 9])
        for point in result['points']:
            self.assertAlmostEqual(point['predicted_stress_pa'], point['shear_stress_pa'])
            self.assertAlmostEqual(point['residual_pa'], 0)
        self.assertLess(result['diagnostics']['rmse_pa'], 1e-12)
        self.assertEqual(result['diagnostics']['evaluations'], 391)
        self.assertEqual(result['diagnostics']['n_step'], 0.005)
        self.assertIn('not proof of uniqueness', result['diagnostics']['warning'])

    def test_zero_yield_noisy_and_boundary_diagnostics(self):
        for dials in [[0, 10, 21, 29], [1, 4, 9, 16]]:
            result = calculate([FannReading(r, d) for r, d in zip([1, 2, 3, 4], dials)])
            self.assertGreater(result['parameters']['flow_behavior_index']['value'], 0)
            self.assertGreaterEqual(result['parameters']['yield_stress_pa']['value'], 0)
            residuals = [p['residual_pa'] for p in result['points']]
            self.assertAlmostEqual(result['diagnostics']['sse_pa2'], sum(r*r for r in residuals))
            self.assertAlmostEqual(result['diagnostics']['rmse_pa'], (sum(r*r for r in residuals)/4)**0.5)
            self.assertAlmostEqual(result['diagnostics']['max_abs_residual_pa'], max(map(abs, residuals)))
        self.assertTrue(result['diagnostics']['at_n_bound'])
        self.assertAlmostEqual(result['parameters']['yield_stress_pa']['value'], 0)

    def test_lower_bound_ambiguity_and_all_readings_are_used(self):
        rates = [1, 2, 4, 8]
        lower = calculate([FannReading(r / 1.70333, r**0.01 / (0.01065 * 47.88025898033584)) for r in rates])
        self.assertEqual(lower['parameters']['flow_behavior_index']['value'], 0.05)
        self.assertTrue(lower['diagnostics']['at_n_bound'])
        ambiguous = calculate([FannReading(r, 1+1e-6*r) for r in rates])
        self.assertGreater(ambiguous['diagnostics']['near_optimal_count'], 1)
        self.assertLess(ambiguous['diagnostics']['near_optimal_n_min'], ambiguous['diagnostics']['near_optimal_n_max'])
        base = [FannReading(r, d) for r, d in [(1, 5), (4, 8), (9, 11)]]
        changed = calculate([*base, FannReading(16, 30)])
        self.assertNotEqual(calculate(base)['parameters'], changed['parameters'])
        self.assertGreater(changed['diagnostics']['sse_pa2'], 0)

    def test_rejects_invalid_degenerate_and_unrepresentable_input(self):
        good = [FannReading(1, 5), FannReading(4, 8), FannReading(9, 11)]
        bad = [None, 'bad', [], good[:2], [*good, good[0]], [object(), *good],
               [FannReading(r, 0) for r in [1, 2, 3]],
               [FannReading(r, 5) for r in [1, 2, 3]],
               [FannReading(r, 4-r) for r in [1, 2, 3]],
               [FannReading(r, d) for r, d in zip([1, 1+1e-10, 1+2e-10], [1, 2, 3])]]
        bad += [[FannReading(v, 1), *good] for v in [True, '1', 0, -1, float('inf'), float('nan'), 10**1000, 1.7e308]]
        bad += [[FannReading(2, v), *good] for v in [True, '1', -1, float('inf'), float('nan'), 10**1000]]
        bad += [[FannReading(r, d*1e200) for r, d in [(1, 5), (4, 8), (9, 12)]]]
        bad += [[FannReading(r, r) for r in range(1, 1002)]]
        for readings in bad:
            with self.subTest(readings=repr(readings)[:100]), self.assertRaises(ValueError):
                calculate(readings)
        self.assertTrue(all(isfinite(p['residual_pa']) for p in calculate(good)['points']))
