"""A complete runtime receipt must identify a fixed source commit."""

from specification_core import PredicateSpec

from native_runtime_context import RuntimeReadyFacts

RUNTIME_READY_SPEC: PredicateSpec[RuntimeReadyFacts] = PredicateSpec(
    lambda facts: (
        facts.artifact_kind == "specgraph_native_runtime"
        and facts.status == "installed"
        and type(facts.schema_version) is int
        and facts.schema_version == 1
        and len(facts.source_commit) == 40
        and all(character in "0123456789abcdef" for character in facts.source_commit)
    ),
    name="native_runtime.receipt_ready",
)
