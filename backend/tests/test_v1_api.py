"""Public V1 API contract tests."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from openoil.main import create_app
from openoil.domain import bit_nozzle_pressure_loss, nozzle_velocity, torque_drag
from test_api import INPUT, expected_result
from test_torque_drag_api import INPUT as TORQUE_INPUT


class V1RouteTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / "cases.sqlite3"
        self.client = self.enterContext(TestClient(create_app(self.database)))

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.json(), body)

    def test_v1_case_list_calculate_save_and_load(self):
        record = {"id": 1, "input": INPUT, "result": expected_result(INPUT)}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assert_response(self.client.get("/api/v1/cases"), 200, [])
            self.assert_response(
                self.client.post("/api/v1/calculate", json=INPUT),
                200,
                expected_result(INPUT),
            )
            self.assert_response(self.client.get("/api/v1/cases"), 200, [])
            self.assert_response(
                self.client.post("/api/v1/cases", json=INPUT), 201, record
            )
            self.assert_response(self.client.get("/api/v1/cases"), 200, [record])
            self.assert_response(self.client.get("/api/v1/cases/1"), 200, record)
        self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))
        with TestClient(create_app(self.database)) as restarted:
            self.assert_response(restarted.get("/api/v1/cases/1"), 200, record)
            self.assert_response(
                restarted.post("/api/v1/cases", json=INPUT), 201, dict(record, id=2)
            )

    def test_v1_studies_match_existing_contracts_without_saving(self):
        studies = [
            ("nozzle-velocity", {"flow_m3_s": 0.01, "total_nozzle_area_m2": 0.001}),
            (
                "bit-nozzle-pressure-loss",
                {
                    "density_kg_m3": 1198.2642731689612,
                    "flow_m3_s": 296 * 0.003785411784 / 60,
                    "total_nozzle_area_m2": 0.0254**2,
                },
            ),
            ("torque-drag", TORQUE_INPUT),
        ]
        for name, data in studies:
            with self.subTest(study=name):
                if name == "nozzle-velocity":
                    expected = {"velocity_m_s": nozzle_velocity.calculate(**data)}
                elif name == "bit-nozzle-pressure-loss":
                    expected = bit_nozzle_pressure_loss.calculate(**data)
                else:
                    expected = asdict(torque_drag.calculate(
                        **dict(data, sections=[torque_drag.Section(**s) for s in data["sections"]])
                    ))
                    expected["sections"] = list(expected["sections"])
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    response = self.client.post(f"/api/v1/{name}/calculate", json=data)
                self.assert_response(response, 200, expected)
                self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))
                self.assert_response(self.client.get("/api/v1/cases"), 200, [])
        self.assert_response(
            self.client.post("/api/v1/cases", json=INPUT),
            201,
            {"id": 1, "input": INPUT, "result": expected_result(INPUT)},
        )


if __name__ == "__main__":
    unittest.main()
