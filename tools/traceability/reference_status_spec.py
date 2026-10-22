"""RFC 0226: resolution requires supported, available and unique source evidence."""

from specification_core import FirstMatch, PredicateSpec

from .context import ReferenceFacts

REFERENCE_STATUS_SPEC: FirstMatch[ReferenceFacts, str] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(lambda c: not c.supported_syntax, name="trace.unsupported_reference"),
            "unsupported",
        ),
        (
            PredicateSpec(lambda c: not c.source_available, name="trace.source_unavailable"),
            "unavailable",
        ),
        (
            PredicateSpec(lambda c: c.candidate_count == 0, name="trace.target_absent"),
            "unresolved",
        ),
        (
            PredicateSpec(lambda c: c.candidate_count > 1, name="trace.target_ambiguous"),
            "ambiguous",
        ),
        (
            PredicateSpec(lambda c: not c.expected_kind, name="trace.wrong_declaration_kind"),
            "wrong_kind",
        ),
    ),
    "resolved",
    name="trace.reference_status",
)
