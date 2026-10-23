"""Independent documented example and bounded domain behavior; no vendor runtime."""
from contextlib import redirect_stderr, redirect_stdout
import io
import unittest

from openoil.domain import bit_nozzle_pressure_loss, nozzle_velocity


EXAMPLE = dict(density_kg_m3=10 * 0.45359237 / 0.003785411784,
               flow_m3_s=296 * 0.003785411784 / 60,
               total_nozzle_area_m2=0.0254 ** 2)


class BitNozzlePressureLossTests(unittest.TestCase):
    def test_documented_example_determinism_units_and_provenance(self):
        original = EXAMPLE.copy()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = bit_nozzle_pressure_loss.calculate(**EXAMPLE)
            self.assertEqual(result, bit_nozzle_pressure_loss.calculate(**EXAMPLE))
        # Independent documented example: 95 ft/s, ~80.7299 psi.
        self.assertAlmostEqual(nozzle_velocity.calculate(EXAMPLE['flow_m3_s'],
                               EXAMPLE['total_nozzle_area_m2']) / 0.3048, 95, places=10)
        self.assertAlmostEqual(result['pressure_loss']['value'], 556612.8, delta=2)
        self.assertAlmostEqual(result['pressure_loss']['value'] / 6894.757293168,
                               80.7299, delta=0.0003)
        self.assertEqual(result['pressure_loss']['quantity'], 'bit_nozzle_pressure_loss')
        self.assertEqual(result['pressure_loss']['unit'], 'Pa')
        self.assertEqual(result['model_id'], 'openoil.hydraulics.documented-bit-nozzle-pressure-loss')
        self.assertEqual(result['model_version'], '1.0.0')
        self.assertEqual(result['input_schema_version'], '1')
        self.assertEqual(result['result_schema_version'], '1')
        self.assertEqual(result['coefficient'], {'symbol': 'Cd', 'value': 0.95, 'unit': '1',
                         'selection': 'fixed documented coefficient'})
        self.assertEqual(result['applicability']['status'], 'supported')
        self.assertIn('single-phase', result['applicability']['assumptions'])
        self.assertEqual(EXAMPLE, original)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))

    def test_rejects_invalid_quantities(self):
        for field in EXAMPLE:
            for value in [0, -1, float('nan'), float('inf'), -float('inf'), True, '1', None]:
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, f'^{field} must be positive and finite$'):
                        bit_nozzle_pressure_loss.calculate(**dict(EXAMPLE, **{field: value}))

    def test_rejects_unrepresentable_results(self):
        for changes in [dict(density_kg_m3=1e308), dict(flow_m3_s=1e308),
                        dict(total_nozzle_area_m2=5e-324), dict(density_kg_m3=5e-324, flow_m3_s=1e-150)]:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, '^calculation outside finite numerical range$'):
                    bit_nozzle_pressure_loss.calculate(**dict(EXAMPLE, **changes))

    def test_pressure_scales_with_density_and_squared_flow(self):
        base = bit_nozzle_pressure_loss.calculate(**EXAMPLE)['pressure_loss']['value']
        for changes, factor in [(dict(density_kg_m3=EXAMPLE['density_kg_m3'] * 2), 2),
                                (dict(flow_m3_s=EXAMPLE['flow_m3_s'] * 2), 4),
                                (dict(total_nozzle_area_m2=EXAMPLE['total_nozzle_area_m2'] * 2), 0.25)]:
            self.assertAlmostEqual(bit_nozzle_pressure_loss.calculate(**dict(EXAMPLE, **changes))['pressure_loss']['value'], base * factor)
