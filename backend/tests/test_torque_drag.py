"""Independent hand calculations for the straight, tension-only SI study."""
import contextlib
from dataclasses import asdict, replace
import io
import json
import math
import re
import unittest

from wellplan_hydraulics import torque_drag as td


class TorqueDragTests(unittest.TestCase):
    def section(self, **changes):
        return replace(td.Section(10.0, 0.2, 1000.0), **changes)

    def calculate(self, sections=None, **changes):
        args = dict(sections=[self.section()] if sections is None else sections,
                    inclination_deg=30.0, density_kg_m3=1000.0,
                    axial_friction_coefficient=0.2,
                    rotational_friction_coefficient=0.3)
        args.update(changes)
        return td.calculate(**args)

    def reject(self, message, sections=None, **changes):
        sections = [self.section()] if sections is None else sections
        before = repr(sections)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, '^' + re.escape(message) + '$'):
                self.calculate(sections, **changes)
        self.assertEqual(repr(sections), before)
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ('', ''))

    def test_inclined_section_contributions_and_surface_totals(self):
        # Each section has 100 N/m submerged weight, by construction.
        # At 30 degrees: N = b L / 2; G = b L sqrt(3) / 2.
        sections = [td.Section(10, 0.2, 100 + 1000 * 9.80665 * math.pi * 0.01),
                    td.Section(20, 0.4, 100 + 1000 * 9.80665 * math.pi * 0.04)]
        before = [asdict(s) for s in sections]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.calculate(sections)
        self.assertEqual(len(result.sections), 2)
        for row, length, radius in zip(result.sections, [10, 20], [0.1, 0.2]):
            gravity = 100 * length * math.sqrt(3) / 2
            normal = 50 * length
            self.assertAlmostEqual(row.submerged_weight_n_m, 100)
            self.assertAlmostEqual(row.axial_gravity_n, gravity)
            self.assertAlmostEqual(row.normal_force_n, normal)
            self.assertAlmostEqual(row.axial_friction_n, 0.2 * normal)
            self.assertAlmostEqual(row.rotational_friction_n, 0.3 * normal)
            self.assertAlmostEqual(row.pickup_tension_n, gravity + 0.2 * normal)
            self.assertAlmostEqual(row.slackoff_tension_n, gravity - 0.2 * normal)
            self.assertAlmostEqual(row.rotating_torque_nm, 0.3 * normal * radius)
        self.assertAlmostEqual(result.pickup_tension_n, 1500 * math.sqrt(3) + 300)
        self.assertAlmostEqual(result.slackoff_tension_n, 1500 * math.sqrt(3) - 300)
        self.assertAlmostEqual(result.rotating_torque_nm, 75)
        for field in ['pickup_tension_n', 'slackoff_tension_n', 'rotating_torque_nm']:
            self.assertAlmostEqual(getattr(result, field),
                                   sum(getattr(row, field) for row in result.sections))
        json.dumps(asdict(result), allow_nan=False)
        self.assertEqual([asdict(s) for s in sections], before)
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ('', ''))

    def test_vertical_contact_drag_and_torque_are_zero(self):
        result = self.calculate(inclination_deg=0)
        row = result.sections[0]
        weight = (1000 - 1000 * 9.80665 * math.pi * 0.01) * 10
        self.assertAlmostEqual(row.axial_gravity_n, weight)
        self.assertEqual((row.normal_force_n, row.axial_friction_n,
                          row.rotational_friction_n, row.rotating_torque_nm), (0, 0, 0, 0))
        self.assertAlmostEqual(result.pickup_tension_n, weight)
        self.assertAlmostEqual(result.slackoff_tension_n, weight)
        self.assertEqual(result.rotating_torque_nm, 0)

    def test_closed_pipe_buoyancy_uses_density_and_od_squared(self):
        for density, diameter in [(0, 0.2), (500, 0.2), (500, 0.4)]:
            with self.subTest(density=density, diameter=diameter):
                row = self.calculate([self.section(pipe_od_m=diameter)],
                                     density_kg_m3=density).sections[0]
                expected = 1000 - density * 9.80665 * math.pi * diameter**2 / 4
                self.assertAlmostEqual(row.submerged_weight_n_m, expected)

    def test_all_inputs_must_be_finite_numbers(self):
        globals_ = ['inclination_deg', 'density_kg_m3', 'axial_friction_coefficient',
                    'rotational_friction_coefficient']
        for field in globals_ + ['length_m', 'pipe_od_m', 'air_weight_n_m']:
            for value in [math.nan, math.inf, -math.inf, True, '1', None]:
                with self.subTest(field=field, value=value):
                    changes = {field: value} if field in globals_ else {
                        'sections': [self.section(**{field: value})]}
                    self.reject(field + ' must be a finite number', **changes)

    def test_sections_are_nonempty_with_positive_length_od_and_air_weight(self):
        self.reject('sections must not be empty', sections=[])
        for field in ['length_m', 'pipe_od_m', 'air_weight_n_m']:
            for value in [0, -1]:
                with self.subTest(field=field, value=value):
                    self.reject(field + ' must be positive',
                                sections=[self.section(**{field: value})])

    def test_density_and_friction_coefficients_are_nonnegative(self):
        for field in ['density_kg_m3', 'axial_friction_coefficient',
                      'rotational_friction_coefficient']:
            with self.subTest(field=field):
                self.reject(field + ' must be nonnegative', **{field: -1})
        result = self.calculate(density_kg_m3=0, axial_friction_coefficient=0,
                                rotational_friction_coefficient=0)
        self.assertEqual(result.pickup_tension_n, result.slackoff_tension_n)
        self.assertEqual(result.rotating_torque_nm, 0)

    def test_inclination_is_from_vertical_in_half_open_range(self):
        for angle in [-1, 90, 180]:
            with self.subTest(angle=angle):
                self.reject('inclination_deg must satisfy 0 <= angle < 90',
                            inclination_deg=angle)
        self.calculate(inclination_deg=89.999, axial_friction_coefficient=0)

    def test_each_section_requires_strictly_positive_submerged_weight(self):
        displaced_weight = 1000 * 9.80665 * (math.pi * 0.2**2 / 4)
        for weight in [displaced_weight, displaced_weight / 2]:
            with self.subTest(weight=weight):
                self.reject('submerged weight must be positive in every section',
                            sections=[self.section(), self.section(air_weight_n_m=weight)])

    def test_negative_slackoff_contributions_are_rejected(self):
        self.reject('slackoff tension must be nonnegative in every section',
                    sections=[self.section(), self.section(length_m=1)],
                    inclination_deg=60, axial_friction_coefficient=1)
        # Choose mu = cot(theta), so the two computed forces cancel exactly.
        angle = math.radians(30)
        coefficient = math.cos(angle) / math.sin(angle)
        result = self.calculate([self.section(length_m=1, air_weight_n_m=1)],
                                density_kg_m3=0, axial_friction_coefficient=coefficient)
        self.assertEqual(result.slackoff_tension_n, 0)

    def test_nonfinite_derived_values_are_rejected(self):
        for sections, changes in [([self.section(pipe_od_m=1e308)], {}),
                                  ([self.section(length_m=1e308)], {}),
                                  ([self.section()], {'rotational_friction_coefficient': 1e308}),
                                  ([self.section(length_m=1, air_weight_n_m=1e308)] * 2,
                                   {'inclination_deg': 0, 'density_kg_m3': 0})]:
            with self.subTest(sections=sections, changes=changes):
                self.reject('calculation outside finite numerical range',
                            sections=sections, **changes)


if __name__ == '__main__':
    unittest.main()
