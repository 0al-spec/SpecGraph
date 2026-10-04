"""Historical partial check from 8bd61fb, not the complete-record policy.

Source: tools/subject_publication.py in commit
8bd61fb772141a7e7005429a275c0c161fd7c59d (pre-06efdb7e).
Only the content/membership conjuncts are reproduced; source-target bindings
are intentionally omitted. The current static matcher does not recognize this
as a near match. This fixture documents that coverage gap, not approval to use it.
"""


def partial_reviewed_record(draft, document, revision, subject):
    draft_revision = draft["revisions"][-1]
    if (
        draft["subject"] == document["subject"]
        and draft["title"] == document["title"]
        and draft_revision["number"] == revision["number"]
        and draft_revision["statement"] == revision["statement"] == subject["statement"]
        and draft_revision["revision_scope"] == revision["revision_scope"]
        and draft_revision["acceptance_criteria_refs"] == revision["acceptance_criteria_refs"]
    ):
        return True
    return False
