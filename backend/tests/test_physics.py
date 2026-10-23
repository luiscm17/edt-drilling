"""Public-interface numerical and rejection tests (stdlib only)."""
import contextlib
from dataclasses import asdict
import io
import math
import unittest

from openoil.domain import physics as p


class PhysicsTests(unittest.TestCase):
    def section(self, length=100.0):
        return p.Section(length_m=length, pipe_id_m=0.08,
                         pipe_od_m=0.10, hole_id_m=0.20)

    def calculate(self, sections=None, **changes):
        args = dict(sections=[self.section()] if sections is None else sections,
                    density_kg_m3=1000.0, viscosity_pa_s=0.1, flow_m3_s=0.001)
        args.update(changes)
        return p.calculate(**args)

    def reject(self, message, **changes):
        sections = changes.pop('sections', [self.section()])
        before = [asdict(section) for section in sections]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, '^' + message + '$'):
                self.calculate(sections, **changes)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual([asdict(section) for section in sections], before)

    def test_pipe_laminar_si(self):
        result = self.calculate()
        row = result.sections[0].pipe
        velocity = 0.001 / (math.pi * 0.08**2 / 4)
        self.assertAlmostEqual(row.velocity_m_s, velocity)
        self.assertAlmostEqual(row.reynolds, 1000 * velocity * 0.08 / 0.1)
        self.assertEqual(row.regime, 'laminar')
        self.assertAlmostEqual(row.darcy_factor, 64 / row.reynolds)
        self.assertAlmostEqual(row.pressure_loss_pa, 128 * 0.1 * 100 * 0.001 /
                               (math.pi * 0.08**4))

    def test_annular_laminar_concentric_solution(self):
        row = self.calculate().sections[0].annulus
        velocity = 0.001 / (math.pi * (0.2**2 - 0.1**2) / 4)
        shape = 0.2**4 - 0.1**4 - (0.2**2 - 0.1**2)**2 / math.log(2)
        expected = 128 * 0.1 * 100 * 0.001 / (math.pi * shape)
        self.assertAlmostEqual(row.velocity_m_s, velocity)
        self.assertAlmostEqual(row.reynolds, 1000 * velocity * 0.1 / 0.1)
        self.assertEqual(row.regime, 'laminar')
        self.assertAlmostEqual(row.pressure_loss_pa, expected)
        self.assertAlmostEqual(row.darcy_factor,
                               2 * expected * 0.1 / (1000 * velocity**2 * 100))

    def test_smooth_turbulent_blasius(self):
        result = self.calculate(viscosity_pa_s=0.001, flow_m3_s=0.002)
        for row, diameter in [(result.sections[0].pipe, 0.08),
                              (result.sections[0].annulus, 0.1)]:
            self.assertEqual(row.regime, 'turbulent')
            self.assertAlmostEqual(row.darcy_factor, 0.3164 / row.reynolds**0.25)
            self.assertAlmostEqual(row.pressure_loss_pa,
                                   row.darcy_factor * 100 / diameter *
                                   1000 * row.velocity_m_s**2 / 2)

    def test_section_totals_hydrostatic_and_ecd(self):
        sections = [self.section(40), self.section(60)]
        before = [asdict(section) for section in sections]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.calculate(sections)
        single = self.calculate()
        self.assertEqual(len(result.sections), 2)
        self.assertEqual(result.depth_m, 100)
        self.assertAlmostEqual(result.pipe_friction_pa, single.pipe_friction_pa)
        self.assertAlmostEqual(result.annular_friction_pa, single.annular_friction_pa)
        self.assertAlmostEqual(result.pipe_friction_pa,
                               sum(r.pipe.pressure_loss_pa for r in result.sections))
        self.assertAlmostEqual(result.annular_friction_pa,
                               sum(r.annulus.pressure_loss_pa for r in result.sections))
        self.assertEqual(result.hydrostatic_pa, 1000 * 9.80665 * 100)
        self.assertAlmostEqual(result.bottomhole_annular_pa,
                               result.hydrostatic_pa + result.annular_friction_pa)
        self.assertAlmostEqual(result.ecd_kg_m3,
                               1000 + result.annular_friction_pa / (9.80665 * 100))
        self.assertEqual([asdict(section) for section in sections], before)
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ('', ''))

    def test_positive_finite_properties_and_flow(self):
        for key in ['density_kg_m3', 'viscosity_pa_s', 'flow_m3_s']:
            for value in [0, -1, math.nan, math.inf, -math.inf, True, '1', None]:
                with self.subTest(key=key, value=value):
                    self.reject(key + ' must be a positive finite number', **{key: value})

    def test_geometry_and_nonempty_sections(self):
        self.reject('sections must not be empty', sections=[])
        for key in ['length_m', 'pipe_id_m', 'pipe_od_m', 'hole_id_m']:
            for value in [0, -1, math.nan, math.inf, True]:
                geometry = asdict(self.section())
                geometry[key] = value
                with self.subTest(key=key, value=value):
                    self.reject(key + ' must be a positive finite number',
                                sections=[p.Section(**geometry)])
        for inner, outer, hole in [(0.1, 0.1, 0.2), (0.11, 0.1, 0.2),
                                   (0.08, 0.2, 0.2), (0.08, 0.3, 0.2)]:
            self.reject('geometry requires pipe_id_m < pipe_od_m < hole_id_m',
                        sections=[p.Section(100, inner, outer, hole)])
        self.reject('annular diameter ratio must be <= 0.8',
                    sections=[p.Section(100, 0.08, 0.17, 0.2)])
        self.calculate(sections=[p.Section(100, 0.08, 0.16, 0.2)])

    def test_regime_boundaries(self):
        # Large hole keeps annular Re laminar while pipe crosses each boundary.
        section = p.Section(100, 0.08, 0.1, 1.0)
        for re, accepted, regime in [(2299, True, 'laminar'), (2300, False, ''),
                                     (3999, False, ''), (4000, True, 'turbulent'),
                                     (100000, True, 'turbulent'), (100001, False, '')]:
            flow = re * math.pi * 0.08 * 0.1 / (4 * 1000)
            with self.subTest(re=re):
                if accepted:
                    result = self.calculate([section], flow_m3_s=flow)
                    self.assertEqual(result.sections[0].pipe.regime, regime)
                else:
                    self.reject('Reynolds number outside supported regimes',
                                sections=[section], flow_m3_s=flow)
        # Annulus alone in transition; pipe is already turbulent.
        self.reject('Reynolds number outside supported regimes',
                    viscosity_pa_s=0.001, flow_m3_s=0.00075)

    def test_unrepresentable_derived_values_rejected(self):
        self.reject('calculation outside finite numerical range',
                    sections=[self.section(1e308), self.section(1e308)])
        self.reject('calculation outside finite numerical range', flow_m3_s=1e-320)


if __name__ == '__main__':
    unittest.main()
