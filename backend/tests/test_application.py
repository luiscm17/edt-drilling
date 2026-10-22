"""Use cases exercised without HTTP, SQLite or a filesystem repository."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import io
import unittest

from wellplan_hydraulics.application import (
    CaseInput, HydraulicsApplication, InvalidCaseId, MissingCase, UnsupportedInput,
)
from wellplan_hydraulics.physics import Section, calculate


def inputs(**changes):
    values = dict(sections=(Section(100, 0.08, 0.10, 0.20),),
                  density_kg_m3=1000, viscosity_pa_s=0.1, flow_m3_s=0.001)
    values.update(changes)
    return CaseInput(**values)


class FakeRepository:
    """Atomic snapshot port with observable calls and ID allocation."""
    def __init__(self):
        self.records = []
        self.calls = []
        self.next_id = 1

    def save(self, inputs, result):
        self.calls.append('save')
        record = deepcopy(dict(id=self.next_id, input=inputs, result=result))
        self.records.append(record)
        self.next_id += 1
        return deepcopy(record)

    def list(self):
        self.calls.append('list')
        return deepcopy(self.records)

    def get(self, case_id):
        self.calls.append(('get', case_id))
        return next((deepcopy(r) for r in self.records if r['id'] == case_id), None)


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.application = HydraulicsApplication(self.repository)

    def test_calculate_is_silent_nonmutating_and_does_not_access_repository(self):
        data = inputs()
        before = deepcopy(data)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = self.application.calculate(data)
        self.assertEqual(result, asdict(calculate(**asdict_for_calculation(data))))
        self.assertEqual(data, before)
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
        self.assertEqual(self.repository.calls, [])
        self.assertEqual(self.application.list(), [])
        self.assertEqual(self.application.save(data)['id'], 1)

    def test_save_list_load_preserve_distinct_snapshots_without_recalculation(self):
        data = inputs()
        result = self.application.calculate(data)
        first = self.application.save(data)
        expected_input = asdict(data)
        expected_input['sections'] = [asdict(s) for s in data.sections]
        self.assertEqual(first, dict(id=1, input=expected_input, result=result))
        self.assertEqual(self.repository.calls, ['save'])
        second = self.application.save(data)
        self.assertEqual(second, dict(first, id=2))
        first['input']['density_kg_m3'] = -1
        first['result']['depth_m'] = -1
        stored = dict(id=1, input=expected_input, result=result)
        self.assertEqual(self.application.load(1), stored)
        self.assertEqual(self.application.list(), [stored, second])
        # Old snapshots need not be valid under today's model; never recalculate.
        self.repository.records[0] = dict(id=1, input={}, result={'legacy': 7})
        self.assertEqual(self.application.load(1), self.repository.records[0])
        self.assertEqual(self.application.list()[0], self.repository.records[0])

    def test_rejected_engineering_input_never_calls_port_or_consumes_id(self):
        first = self.application.save(inputs())
        cases = [
            (inputs(density_kg_m3=0), 'density_kg_m3 must be a positive finite number'),
            (inputs(viscosity_pa_s=-1), 'viscosity_pa_s must be a positive finite number'),
            (inputs(flow_m3_s=float('nan')), 'flow_m3_s must be a positive finite number'),
            (inputs(sections=()), 'sections must not be empty'),
            (inputs(sections=(Section(100, .1, .1, .2),)),
             'geometry requires pipe_id_m < pipe_od_m < hole_id_m'),
            (inputs(sections=(Section(100, .08, .17, .2),)),
             'annular diameter ratio must be <= 0.8'),
            (inputs(flow_m3_s=.02), 'Reynolds number outside supported regimes'),
            (inputs(sections=(Section(1e308, .08, .1, .2),)),
             'calculation outside finite numerical range'),
        ]
        for data, message in cases:
            for operation in [self.application.calculate, self.application.save]:
                with self.subTest(operation=operation.__name__, message=message):
                    calls = deepcopy(self.repository.calls)
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        with self.assertRaises(UnsupportedInput) as caught:
                            operation(data)
                    self.assertEqual(str(caught.exception), message)
                    self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))
                    self.assertEqual(self.repository.calls, calls)
                    self.assertEqual(self.application.list(), [first])
                    self.assertEqual(self.repository.next_id, 2)
        self.assertEqual(self.application.save(inputs())['id'], 2)

    def test_load_validates_ids_before_port_and_distinguishes_missing_case(self):
        for case_id in [0, -1, 9223372036854775808, True, '1']:
            with self.subTest(case_id=case_id):
                with self.assertRaises(InvalidCaseId) as caught:
                    self.application.load(case_id)
                self.assertEqual(str(caught.exception), 'invalid case id')
                self.assertEqual(self.repository.calls, [])
        for case_id in [1, 9223372036854775807]:
            with self.assertRaises(MissingCase) as caught:
                self.application.load(case_id)
            self.assertEqual(str(caught.exception), 'case not found')
        self.assertEqual(self.application.list(), [])
        self.assertEqual(self.application.save(inputs())['id'], 1)

    def test_repository_failures_are_not_engineering_errors(self):
        def fail(*args):
            raise OSError('repository unavailable')
        for method, operation in [
            ('save', lambda: self.application.save(inputs())),
            ('list', self.application.list),
            ('get', lambda: self.application.load(1)),
        ]:
            setattr(self.repository, method, fail)
            with self.assertRaisesRegex(OSError, '^repository unavailable$'):
                operation()
        self.assertEqual(self.repository.next_id, 1)


def asdict_for_calculation(data):
    return dict(sections=data.sections, density_kg_m3=data.density_kg_m3,
                viscosity_pa_s=data.viscosity_pa_s, flow_m3_s=data.flow_m3_s)
