"""Guard layer dependency direction and the explicit Python package layout."""

import ast
import importlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "src" / "openoil"


class ArchitectureTests(unittest.TestCase):
    def test_core_and_http_dependencies_point_inward(self):
        allowed = {
            "domain": {"collections.abc", "dataclasses", "math", "openoil.domain"},
            "application": {
                "__future__",
                "collections.abc",
                "dataclasses",
                "datetime",
                "typing",
                "openoil.domain",
                "openoil.application",
            },
            "adapters/inbound/http": {
                "dataclasses",
                "typing",
                "fastapi",
                "pydantic",
                "openoil.domain",
                "openoil.application",
                "openoil.adapters.inbound.http",
            },
        }
        for directory, prefixes in allowed.items():
            for path in (ROOT / directory).rglob("*.py"):
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        self.assertEqual(node.level, 0, str(path))
                        modules = [node.module]
                    else:
                        continue
                    for module in modules:
                        self.assertIsNotNone(module)
                        self.assertTrue(
                            any(
                                module == prefix or module.startswith(prefix + ".")
                                for prefix in prefixes
                            ),
                            (str(path), module),
                        )

    def test_package_layout_and_entrypoint_are_explicit(self):
        self.assertTrue((ROOT / "domain").is_dir())
        self.assertTrue((ROOT / "application").is_dir())
        self.assertTrue((ROOT / "adapters/inbound/http").is_dir())
        self.assertTrue((ROOT / "adapters/outbound").is_dir())
        self.assertFalse((ROOT / "api.py").exists())
        self.assertFalse((ROOT / "storage.py").exists())
        entrypoint = importlib.import_module("openoil.main")
        self.assertTrue(callable(entrypoint.create_app))
        self.assertIsNotNone(entrypoint.app)
