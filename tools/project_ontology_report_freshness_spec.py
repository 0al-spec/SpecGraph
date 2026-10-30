"""Decision over explicitly captured advisory-report comparisons."""

from dataclasses import dataclass

from specification_core import PredicateSpec


@dataclass(frozen=True, slots=True)
class FreshnessFacts:
    comparisons: tuple[bool, ...]


REPORT_INPUTS_COMPATIBLE_SPEC = PredicateSpec[FreshnessFacts](
    lambda facts: bool(facts.comparisons) and all(facts.comparisons),
    name="project_ontology_report.inputs_compatible",
)
