"""Immutable facts prepared by the publication JSON/XML adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BindingContext:
    passport_ids: frozenset[str]
    requirement_ids: frozenset[str]
    bound_ids: tuple[str, ...]
    selectors: tuple[str, ...]


@dataclass(frozen=True)
class TestCaseContext:
    occurrence_count: int
    failed: bool
    skipped: bool


@dataclass(frozen=True)
class TestSuiteContext:
    exit_code: int | None
    outcomes: frozenset[str]
    observed_count: int
    required_count: int
    declared_result: str = "observed_success"


@dataclass(frozen=True)
class SourceIdentity:
    repository: str
    revision: str
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SnapshotContext:
    expected: SourceIdentity
    observed: SourceIdentity


@dataclass(frozen=True)
class ExecutionIdentity:
    provider: str
    run_id: str
    run_attempt: str
    uri: str


@dataclass(frozen=True)
class TestObservationContext:
    expected_source: SourceIdentity
    observed_source: SourceIdentity
    expected_execution: ExecutionIdentity
    observed_execution: ExecutionIdentity
    expected_obligations: tuple[tuple[str, str], ...]
    observed_obligations: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HttpObservationContext:
    source_revision: str
    observed_source_revision: str
    expected_execution: ExecutionIdentity
    observed_execution: ExecutionIdentity
    observer_environment: str
    expected_bundle: tuple[str, str] | None
    observed_bundle: tuple[str, str] | None
    expected_origin: str
    observed_origin: str
    status: str
    artifact_kind: str
    expected_file_count: int
    verified_file_count: int | None
    verified_metadata_count: int | None
    failure_count: int | None


@dataclass(frozen=True)
class MergedRevisionContext:
    merged_at: str
    expected_revision: str
    observed_revision: str
    expected_repository: str
    observed_repository: str
    pull_number: int
