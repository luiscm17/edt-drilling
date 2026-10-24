import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from openoil.domain import bingham_rheology

VALID_READINGS = [
    bingham_rheology.FannReading(rpm=600, dial=75),
    bingham_rheology.FannReading(rpm=300, dial=50),
    bingham_rheology.FannReading(rpm=100, dial=25),
]


class BinghamRheologyTests(unittest.TestCase):
    def test_derives_si_bingham_parameters_and_sorted_observation_points(self):
        original = list(VALID_READINGS)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = bingham_rheology.calculate(VALID_READINGS)
        stress_pa_per_dial = 0.01065 * 47.88025898033584
        expected_pv = 25 * stress_pa_per_dial / (1.70333 * 300)
        expected_yp = (2 * 50 - 75) * stress_pa_per_dial
        self.assertAlmostEqual(result["plastic_viscosity"]["value"], expected_pv)
        self.assertEqual(result["plastic_viscosity"]["unit"], "Pa·s")
        self.assertAlmostEqual(result["yield_point"]["value"], expected_yp)
        self.assertEqual(result["yield_point"]["unit"], "Pa")
        self.assertEqual(
            [point["rpm"] for point in result["readings"]], [100, 300, 600]
        )
        self.assertEqual(
            [point["shear_rate_s_inv"] for point in result["readings"]],
            [1.70333 * 100, 1.70333 * 300, 1.70333 * 600],
        )
        self.assertAlmostEqual(
            result["readings"][1]["shear_stress_pa"], 50 * stress_pa_per_dial
        )
        self.assertEqual(result["model_id"], "openoil.rheology.fann-bingham")
        self.assertEqual(result["model_version"], "1.0.0")
        self.assertEqual(result["input_schema_version"], "1")
        self.assertEqual(result["result_schema_version"], "1")
        self.assertEqual(result["applicability"]["status"], "supported")
        self.assertIn("300 and 600 rpm", result["applicability"]["assumptions"])
        self.assertIn(
            "not validated for field decisions", result["applicability"]["limitations"]
        )
        self.assertEqual(VALID_READINGS, original)
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))

    def test_rejects_missing_duplicate_and_invalid_readings(self):
        cases = [
            ([], "readings must contain at least 300 and 600 rpm"),
            (
                [bingham_rheology.FannReading(600, 75)],
                "readings must contain at least 300 and 600 rpm",
            ),
            (
                [
                    bingham_rheology.FannReading(600, 75),
                    bingham_rheology.FannReading(600, 70),
                ],
                "rpm readings must be unique",
            ),
            (
                [
                    bingham_rheology.FannReading(300, 50),
                    bingham_rheology.FannReading(400, 55),
                ],
                "readings must include 300 and 600 rpm",
            ),
        ]
        for readings, message in cases:
            with (
                self.subTest(readings=readings),
                self.assertRaisesRegex(ValueError, f"^{message}$"),
            ):
                bingham_rheology.calculate(readings)

        for rpm, dial, message in [
            (0, 10, "rpm must be positive and finite"),
            (-1, 10, "rpm must be positive and finite"),
            (float("nan"), 10, "rpm must be positive and finite"),
            (float("inf"), 10, "rpm must be positive and finite"),
            (True, 10, "rpm must be positive and finite"),
            (300, -1, "dial must be nonnegative and finite"),
            (300, float("nan"), "dial must be nonnegative and finite"),
            (300, float("inf"), "dial must be nonnegative and finite"),
            (300, True, "dial must be nonnegative and finite"),
        ]:
            readings = [
                bingham_rheology.FannReading(300, 50),
                bingham_rheology.FannReading(600, 75),
            ]
            readings[0] = bingham_rheology.FannReading(rpm, dial)
            with (
                self.subTest(rpm=rpm, dial=dial),
                self.assertRaisesRegex(ValueError, f"^{message}$"),
            ):
                bingham_rheology.calculate(readings)

    def test_rejects_negative_derived_pv_or_yield_point(self):
        for readings, message in [
            (
                [
                    bingham_rheology.FannReading(300, 60),
                    bingham_rheology.FannReading(600, 50),
                ],
                "derived plastic viscosity must be nonnegative",
            ),
            (
                [
                    bingham_rheology.FannReading(300, 30),
                    bingham_rheology.FannReading(600, 70),
                ],
                "derived yield point must be nonnegative",
            ),
        ]:
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, f"^{message}$"),
            ):
                bingham_rheology.calculate(readings)

    def test_allows_zero_pv_and_zero_yield_point_in_standalone_study(self):
        zero_pv = bingham_rheology.calculate(
            [
                bingham_rheology.FannReading(300, 50),
                bingham_rheology.FannReading(600, 50),
            ]
        )
        self.assertEqual(zero_pv["plastic_viscosity"]["value"], 0)
        zero_yp = bingham_rheology.calculate(
            [
                bingham_rheology.FannReading(300, 50),
                bingham_rheology.FannReading(600, 100),
            ]
        )
        self.assertEqual(zero_yp["yield_point"]["value"], 0)

    def test_rejects_unrepresentable_derived_values(self):
        with self.assertRaisesRegex(
            ValueError, "^calculation outside finite numerical range$"
        ):
            bingham_rheology.calculate(
                [
                    bingham_rheology.FannReading(300, 1e308),
                    bingham_rheology.FannReading(600, 1e308),
                ]
            )


if __name__ == "__main__":
    unittest.main()
