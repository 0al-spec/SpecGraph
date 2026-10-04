"""Adapter-equivalent copy of the full-record policy; not historical source."""

from subject_publication import scope_digest


def copied_reviewed_record(reviewed_record, requested_record):
    if scope_digest(reviewed_record) == scope_digest(requested_record):
        return True
    return False
