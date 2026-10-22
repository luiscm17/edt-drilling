"""Application-owned atomic case snapshot boundary; no storage-specific APIs."""
from typing import Any, Protocol

Snapshot = dict[str, Any]


class CaseRepository(Protocol):
    """Save atomically; return detached snapshots, ordered by ID when listing.

    Failed saves must not change records or consume an ID. Implementations must
    reject nonfinite serialization and propagate infrastructure failures.
    """

    def save(self, inputs: Snapshot, result: Snapshot) -> Snapshot: ...

    def list(self) -> list[Snapshot]: ...

    def get(self, case_id: int) -> Snapshot | None: ...
