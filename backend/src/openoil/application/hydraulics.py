"""Hydraulics use cases, independent of HTTP and concrete persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from openoil.application.model_identity import provenance
from openoil.domain.physics import Section, calculate
from openoil.application.ports import CaseRepository, Snapshot


class UnsupportedInput(ValueError):
    """Input is outside the engineering model's supported domain."""


class InvalidCaseId(ValueError):
    """Case identifier is outside the supported positive signed 64-bit range."""


class MissingCase(LookupError):
    """No saved snapshot exists for this valid identifier."""


@dataclass(frozen=True)
class CaseInput:
    sections: tuple[Section, ...]
    density_kg_m3: float
    viscosity_pa_s: float
    flow_m3_s: float

    def snapshot(self) -> Snapshot:
        values = asdict(self)
        values["sections"] = [asdict(section) for section in self.sections]
        return values


class HydraulicsApplication:
    def __init__(self, repository: CaseRepository):
        self.repository = repository

    @staticmethod
    def calculate(inputs: CaseInput) -> Snapshot:
        try:
            return asdict(
                calculate(
                    inputs.sections,
                    inputs.density_kg_m3,
                    inputs.viscosity_pa_s,
                    inputs.flow_m3_s,
                )
            )
        except ValueError as error:
            raise UnsupportedInput(str(error)) from None

    @staticmethod
    def _public_case(record: Snapshot) -> Snapshot:
        return {key: record[key] for key in ("id", "input", "result")}

    def _snapshot_with_provenance(self, inputs: CaseInput) -> Snapshot:
        return dict(
            input=inputs.snapshot(),
            result=self.calculate(inputs),
            provenance=provenance(),
        )

    def save(self, inputs: CaseInput) -> Snapshot:
        snapshot = self._snapshot_with_provenance(inputs)
        record = self.repository.save(
            snapshot["input"], snapshot["result"], snapshot["provenance"]
        )
        return self._public_case(record)

    def list(self) -> list[Snapshot]:
        return [self._public_case(record) for record in self.repository.list()]

    def load(self, case_id: int) -> Snapshot:
        if (
            not isinstance(case_id, int)
            or isinstance(case_id, bool)
            or not 1 <= case_id <= 9223372036854775807
        ):
            raise InvalidCaseId("invalid case id")
        record = self.repository.get(case_id)
        if record is None:
            raise MissingCase("case not found")
        return self._public_case(record)
