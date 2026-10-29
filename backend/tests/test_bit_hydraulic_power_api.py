"""Public calculate-only power contract and adjacent pressure-loss regression."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from openoil.main import create_app


class BitHydraulicPowerApiTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = self.enterContext(TestClient(create_app(Path(temp.name) / "cases.sqlite3")))

    def test_explicit_pipe_or_annulus_loss_produces_documented_power_without_saving(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            for boundary in ("pipe", "annulus"):
                with self.subTest(boundary=boundary):
                    response = self.client.post("/api/v1/bit-hydraulic-power/calculate", json={
                        "flow_m3_s": 0.003785411784 / 60,
                        "pressure_loss_pa": 6894.757293168,
                        "pressure_boundary": boundary,
                    })
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.headers["content-type"], "application/json")
                    body = response.json()
                    self.assertEqual(body["pressure_boundary"], boundary)
                    self.assertEqual(body["power"]["quantity"], "hydraulic_power")
                    self.assertEqual(body["power"]["unit"], "hp")
                    self.assertAlmostEqual(body["power"]["value"], 1 / 1714, places=12)
                    self.assertEqual(body["model_id"], "openoil.hydraulics.documented-pressure-loss-power")
                    self.assertEqual(body["model_version"], "1.0.0")
                    self.assertEqual(body["input_schema_version"], "1")
                    self.assertEqual(body["result_schema_version"], "1")
                    self.assertEqual(body["applicability"]["status"], "supported")
                    self.assertIn("not bit", body["applicability"]["limitations"].lower())
                    self.assertEqual(self.client.get("/api/v1/cases").json(), [])
        self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))

    def test_rejections_leave_case_ledger_unchanged(self):
        baseline = {"flow_m3_s": 0.01, "pressure_loss_pa": 1000, "pressure_boundary": "pipe"}
        for delta, detail in [
            ({"flow_m3_s": 0}, "invalid request body"),
            ({"pressure_loss_pa": -1}, "invalid request body"),
            ({"pressure_boundary": "bit"}, "invalid request body"),
            ({"pressure_boundary": ""}, "invalid request body"),
            ({"unexpected": 1}, "invalid request body"),
            ({"flow_m3_s": 1e300, "pressure_loss_pa": 1e300}, "calculation outside finite numerical range"),
        ]:
            with self.subTest(delta=delta):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    response = self.client.post("/api/v1/bit-hydraulic-power/calculate", json=baseline | delta)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(response.headers["content-type"], "application/json")
                    self.assertEqual(response.json(), {"detail": detail})
                    self.assertEqual(self.client.get("/api/v1/cases").json(), [])
                self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))

    def test_existing_bit_loss_still_returns_its_own_pressure(self):
        response = self.client.post("/api/v1/bit-nozzle-pressure-loss/calculate", json={
            "density_kg_m3": 1000, "flow_m3_s": 0.01, "total_nozzle_area_m2": 0.001,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["pressure_loss"]["quantity"], "bit_nozzle_pressure_loss")
        self.assertEqual(self.client.get("/api/v1/cases").json(), [])


if __name__ == "__main__":
    unittest.main()
