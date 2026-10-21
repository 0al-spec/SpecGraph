"""SG-SPEC-0071 / PE-BINDINGS: one explicit test per criterion."""

from specification_core import FirstMatch, PredicateSpec

from .context import BindingContext

BINDING_ERROR_SPEC: FirstMatch[BindingContext, str | None] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: c.passport_ids != c.requirement_ids, name="publication.criteria_drift"
            ),
            "passport criteria must match the canonical pilot requirement",
        ),
        (
            PredicateSpec(
                lambda c: (
                    not c.bound_ids
                    or len(c.bound_ids) != len(set(c.bound_ids))
                    or set(c.bound_ids) != c.passport_ids
                ),
                name="publication.incomplete_bindings",
            ),
            "bindings must cover every passport criterion exactly once",
        ),
        (
            PredicateSpec(
                lambda c: (
                    len(c.selectors) != len(set(c.selectors))
                    or any("::" not in selector for selector in c.selectors)
                ),
                name="publication.ambiguous_test_selectors",
            ),
            "each binding must name a distinct explicit pytest function",
        ),
    ),
    None,
    name="publication.binding_error",
)
