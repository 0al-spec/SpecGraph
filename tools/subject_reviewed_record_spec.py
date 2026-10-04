"""Publication preserves the complete record covered by packet review."""

from specification_core import PredicateSpec

from subject_publication_context import ReviewedRecordContext

REVIEWED_RECORD_SPEC: PredicateSpec[ReviewedRecordContext] = PredicateSpec(
    lambda context: context.reviewed_scope_sha256 == context.requested_scope_sha256,
    name="subject_publication.complete_reviewed_record",
)
