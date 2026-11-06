"""Criterion collection remains distinguishable through the shared snapshot API."""

from dataclasses import replace

from test_criterion_observation_provider import (
    PROFILE,
    PROVIDER_ID,
    EvidenceRegistry,
    EvidenceRequest,
    EvidenceScope,
    PrevalidatedFixture,
    RetainedCriterionEvidenceProvider,
)
from test_criterion_observation_provider import retained as retained


def snapshot(retained, selection):
    request = EvidenceRequest(
        retained.root,
        EvidenceScope("demo/project", retained.scope["revision"], ("TEST-SPEC-0001",), PROFILE),
        criterion_selection=selection,
    )
    return EvidenceRegistry((RetainedCriterionEvidenceProvider(PrevalidatedFixture()),)).collect(
        request, (PROVIDER_ID,)
    )


def test_shared_snapshot_reports_criterion_execution_capability(retained):
    payload = snapshot(retained, retained.select()).to_payload()
    assert payload["profile"] == "specgraph.trace-snapshot/criterion-observations-v1"
    assert payload["execution"] == "retained_artifacts"
    assert payload["admission"] == "not_evaluated"
    assert payload["canonical_mutations_allowed"] is False
    assert payload["observed_subject_count"] == 0  # Criterion rows are not SVC atoms.


def test_missing_journal_preserves_capability_and_unavailable_rows(retained):
    selection = replace(retained.select(), journals=())
    payload = snapshot(retained, selection).to_payload()
    assert payload["profile"] == "specgraph.trace-snapshot/criterion-observations-v1"
    rows = payload["reports"][0]["criterion"]["criteria"]
    assert len(rows) == 3
    assert all(row["binding_integrity"] == "unavailable" for row in rows)
    assert all(row["observed_outcome"] == "unavailable" for row in rows)
