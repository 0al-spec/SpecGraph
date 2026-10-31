"""Reviewed SG-SPEC-0072 examples and their production fixture inputs."""

from dataclasses import dataclass

Role = tuple[str, str]


@dataclass(frozen=True)
class Scenario:
    id: str
    model: str
    mapping: str
    feature: str
    outcome: str
    roles: tuple[Role, ...]
    clauses: tuple[tuple[str, str], ...]
    member_count: int
    supply_compiler: bool
    closure_link: tuple[Role, Role] | None = None
    profile: str = "ontologyc-structural-v1"
    member_source: str | None = None
    partial_rows: tuple[int, ...] = (2,)
    reference: tuple[str, str, str] | None = None


CONTRACT = "/specification/verification_contract/"
SHARED_CLAUSES = (
    (
        CONTRACT + "unavailable",
        "a required compiler, input or dependency check is missing or unsupported",
    ),
    (CONTRACT + "outcome_precedence", "retain per-check diagnostics in every case."),
    (
        CONTRACT + "result_contract",
        "per-check results, one overall outcome, and concrete diagnostics.",
    ),
)

MIXED = Scenario(
    id="SG72-MIXED",
    model="model.ts",
    mapping="source-map.json",
    feature="mixed-outcome.feature",
    outcome="invalid",
    roles=(("selection", "invalid"), ("compiler", "unavailable")),
    clauses=(
        *SHARED_CLAUSES,
        (CONTRACT + "invalid", "duplicate identity"),
        (
            CONTRACT + "outcome_precedence",
            "A detected invalidity makes the overall outcome invalid "
            "even if another required check is unavailable.",
        ),
        (
            "/specification/acceptance_cases/4/expected",
            "a detected context conflict plus another unavailable required check remains invalid "
            "with both diagnostics retained.",
        ),
    ),
    member_count=2,
    supply_compiler=False,
)
MEMBER = ("member_capture", "verified")
CLOSURE = ("dependency_closure", "unavailable")
UNSUPPORTED_CLOSURE = Scenario(
    id="SG72-UNSUPPORTED-CLOSURE",
    model="unsupported-closure.ts",
    mapping="unsupported-closure.source-map.json",
    feature="unsupported-closure.feature",
    outcome="unavailable",
    roles=(MEMBER, CLOSURE),
    clauses=(
        *SHARED_CLAUSES,
        (
            CONTRACT + "outcome_precedence",
            "Otherwise any missing or unsupported required check makes it unavailable.",
        ),
        (
            "/specification/acceptance_cases/3/expected",
            "Successful independent package checks cannot upgrade unsupported closure to verified.",
        ),
    ),
    member_count=1,
    supply_compiler=True,
    closure_link=(CLOSURE, MEMBER),
)
FOUNDATION = ("dependency_closure", "verified")
VERIFIED = Scenario(
    id="SG72-PINNED-FOUNDATION",
    model="pinned-foundation.ts",
    mapping="pinned-foundation.source-map.json",
    feature="pinned-foundation.feature",
    outcome="verified",
    roles=(MEMBER, FOUNDATION),
    clauses=(
        (CONTRACT + "verified", "including required dependency closure and name resolution."),
        (CONTRACT + "outcome_precedence", "Only all required checks succeeding permits verified"),
        (
            "/specification/acceptance_cases/0/expected",
            "An explicitly selected single package with captured source/IR "
            "and all required checks passing is verified for the declared scope",
        ),
    ),
    member_count=1,
    supply_compiler=True,
    closure_link=(FOUNDATION, MEMBER),
    profile="ontologyc-foundation-v1",
    member_source="foundation-member.yaml",
    partial_rows=(0, 2),
    reference=(
        "/spec/classes/Entry/extends",
        "sg:ValueObject",
        "ontology://specgraph.foundation/0.1.0/classes/ValueObject",
    ),
)
CASES = {case.id: case for case in (MIXED, UNSUPPORTED_CLOSURE, VERIFIED)}
