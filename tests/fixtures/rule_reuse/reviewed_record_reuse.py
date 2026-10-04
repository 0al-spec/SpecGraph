"""Explicit Specification reuse, including an imported alias."""

from subject_publication_context import ReviewedRecordContext
from subject_reviewed_record_spec import REVIEWED_RECORD_SPEC as RECORD_POLICY


def reused_reviewed_record(reviewed_sha256, requested_sha256):
    if RECORD_POLICY.is_satisfied_by(ReviewedRecordContext(reviewed_sha256, requested_sha256)):
        return True
    return False
