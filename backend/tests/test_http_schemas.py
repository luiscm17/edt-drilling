"""Stable public schema constraints for inbound HTTP payloads."""
import unittest

from pydantic import ValidationError

from openoil.adapters.inbound.http.schemas import BitNozzleCoefficient


class HttpSchemaTests(unittest.TestCase):
    def test_bit_nozzle_coefficient_is_exactly_point_nine_five(self):
        fixed = {'symbol': 'Cd', 'value': 0.95, 'unit': '1',
                 'selection': 'fixed documented coefficient'}
        self.assertEqual(BitNozzleCoefficient.model_validate(fixed).value, 0.95)
        for value in (0.949, 0.951):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                BitNozzleCoefficient.model_validate(dict(fixed, value=value))

        value_schema = BitNozzleCoefficient.model_json_schema()['properties']['value']
        self.assertEqual(value_schema['minimum'], 0.95)
        self.assertEqual(value_schema['maximum'], 0.95)


if __name__ == '__main__':
    unittest.main()
