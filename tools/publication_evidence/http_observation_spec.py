"""SG-SPEC-0071 / PE-HTTP, PE-OBSERVER: matching publication observation."""

from specification_core import PredicateSpec

from .context import HttpObservationContext

HTTP_OBSERVATION_SPEC: PredicateSpec[HttpObservationContext] = PredicateSpec(
    lambda c: (
        c.expected_bundle is not None
        and c.observed_bundle == c.expected_bundle
        and c.observed_origin == c.expected_origin
        and c.status == "verified"
        and c.artifact_kind == "specgraph_static_artifact_remote_verification_report"
        and c.verified_file_count == c.expected_file_count
        and c.verified_metadata_count == 2
        and c.failure_count == 0
        and bool(
            c.observed_execution.provider and c.observer_environment and c.observed_execution.uri
        )
        and bool(c.source_revision)
        and c.observed_source_revision == c.source_revision
        and (
            not c.expected_execution.run_id
            or (
                c.observed_execution.run_id == c.expected_execution.run_id
                and c.observed_execution.run_attempt == c.expected_execution.run_attempt
            )
        )
    ),
    name="publication.http_observation_matches",
)
