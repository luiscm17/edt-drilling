"""Runtime configuration reads only the current project-scoped database setting."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openoil.adapters.config.settings import Settings


class RuntimeSettingsTests(unittest.TestCase):
    def test_database_path_uses_openoil_environment_setting(self):
        with TemporaryDirectory() as directory:
            database = Path(directory) / 'cases.sqlite3'
            with patch.dict(os.environ, {'OPENOIL_DB_PATH': str(database)}):
                self.assertEqual(Settings().database_path, str(database))

    def test_database_path_defaults_to_local_cases_file(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Settings().database_path, 'cases.sqlite3')
