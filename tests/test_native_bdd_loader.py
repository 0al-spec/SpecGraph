"""RFC 0223 native contract: Given/When/Then at the explicit loader boundary."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_bdd import load_native_bdd as native_load


def load_native_bdd(source, **kwargs):
    return native_load(source, profile=kwargs.pop("profile", "bdd_scenarios_v1"), **kwargs)


def source(scenarios=None, *, alternate=False, references=()):
    spec = {} if scenarios is None else {"bdd_scenarios": scenarios}
    if alternate:
        spec["scenarios"] = []
    if references:
        spec["observability"] = {"obligations": [{"scenario_ids": list(references)}]}
    return yaml.safe_dump({"specification": spec})


@pytest.mark.parametrize(
    "case,raw,presence,codes",
    [
        ("BDD-NATIVE-ABSENT", source(), "absent", []),
        ("BDD-NATIVE-EMPTY", source([]), "explicit_empty", []),
        ("BDD-NATIVE-ALTERNATE", source(alternate=True), "invalid", ["unsupported_container"]),
        ("BDD-NATIVE-AMBIGUOUS", source([], alternate=True), "invalid", ["ambiguous_container"]),
        (
            "BDD-NATIVE-DUPLICATE-KEY",
            "specification: {}\nspecification: {}\n",
            "invalid",
            ["duplicate_yaml_key"],
        ),
        (
            "BDD-NATIVE-LOCAL-REFERENCE",
            source([], references=("sibling-only",)),
            "invalid",
            ["unresolved_node_local_reference"],
        ),
        (
            "BDD-NATIVE-UNKNOWN-FIELD",
            source([{"id": "A", "steps": ["Given"], "extra": True}]),
            "invalid",
            ["unsupported_field"],
        ),
        (
            "BDD-NATIVE-COMBINED-ERROR",
            source([{"id": "A", "steps": [], "extra": True}]),
            "invalid",
            ["unsupported_field", "invalid_value"],
        ),
    ],
)
def test_contract_cases(case, raw, presence, codes):
    result = load_native_bdd(raw)
    assert result.presence.value == presence, case
    assert [f.code for f in result.findings] == codes, case
    assert result.extracted_count == (None if codes else 0)
    assert len(result.policies) == 6


def test_exact_steps_and_no_authority():
    result = load_native_bdd(
        source(
            [{"id": " A ", "scenario": " title ", "steps": [" Given ", " Given "]}],
            references=(" A ",),
        )
    )
    assert result.scenarios[0].id == " A "
    assert result.scenarios[0].steps == (" Given ", " Given ")
    assert result.extracted_count == 1
    assert result.canonical_mutations_allowed is False
    assert result.code_mutations_allowed is False
    assert result.evidence_status == "not_evaluated"
    assert all(p.outcome == "satisfied" for p in result.policies)
    assert "Given" not in repr(result.events)
    assert "title" not in repr(result.events)


def test_unknown_profile_skips_without_fallback():
    result = load_native_bdd(source([]), profile="future")
    assert [f.code for f in result.findings] == ["unsupported_profile"]
    assert result.policies[0].outcome == "unsatisfied"
    assert all(p.skip_reason == "unsupported_profile" for p in result.policies[1:])


@pytest.mark.parametrize("field", ["id", "scenario", "steps", "reference"])
def test_timestamp_original_types(field):
    from datetime import date

    entry = {"id": "A", "scenario": "title", "steps": ["Given"]}
    references = (date(2026, 10, 2),) if field == "reference" else ()
    if field == "steps":
        entry[field] = [date(2026, 10, 2)]
    elif field != "reference":
        entry[field] = date(2026, 10, 2)
    result = load_native_bdd(source([entry], references=references))
    assert result.presence.value == "invalid"
    assert "invalid_value" in [f.code for f in result.findings]


@pytest.mark.parametrize(
    "entries",
    [
        [None],
        [{"id": "", "steps": ["Given"]}],
        [{"id": "A", "steps": None}],
        [{"id": "A", "steps": [" "]}],
        [{"id": "A", "scenario": None, "steps": ["Given"]}],
    ],
)
def test_malformed_values(entries):
    result = load_native_bdd(source(entries))
    assert result.presence.value == "invalid"
    assert result.extracted_count is None


def test_duplicate_ids_skip_references():
    result = load_native_bdd(source([{"id": "A", "steps": ["Given"]}] * 2, references=("missing",)))
    assert [f.code for f in result.findings] == ["duplicate_scenario_id"]
    assert result.policies[-1].skip_reason == "duplicate_scenario_ids"


def test_combined_errors_do_not_skip_ids():
    result = load_native_bdd(source([{"id": "A", "steps": [], "extra": True}]))
    assert [p.outcome for p in result.policies] == [
        "satisfied",
        "satisfied",
        "unsatisfied",
        "unsatisfied",
        "satisfied",
        "satisfied",
    ]


@pytest.mark.parametrize("container", [None, False, 7, "wrong", {}])
def test_invalid_container(container):
    result = load_native_bdd(yaml.safe_dump({"specification": {"bdd_scenarios": container}}))
    assert [f.code for f in result.findings] == ["invalid_container_type"]
    assert all(p.skip_reason == "invalid_container" for p in result.policies[2:])


def test_reference_findings_follow_input_order():
    raw = yaml.safe_dump(
        {
            "specification": {
                "observability": {
                    "obligations": [{"scenario_ids": ["missing"]}, {"scenario_ids": None}]
                }
            }
        }
    )
    result = load_native_bdd(raw)
    assert [f.code for f in result.findings] == ["unresolved_node_local_reference", "invalid_value"]


def test_repeated_values_keep_exact_order_and_diagnostic_trace():
    from specification_core import TraceRecorder

    recorder = TraceRecorder()
    result = load_native_bdd(source([{"id": "A", "steps": ["Given", "Given"]}]), recorder=recorder)
    assert len(result.policies) == 6
    assert len(recorder.events) == 6
    assert result == load_native_bdd(source([{"id": "A", "steps": ["Given", "Given"]}]))
    assert result.presence.value == "present"
    assert all(p.rule_ref.startswith("SG-RFC-0223.native.") for p in result.policies)


def test_prepared_thirteen_scenarios_are_valid_native_input():
    path = (
        Path(__file__).resolve().parents[1]
        / "docs/reviews/0223_native_bdd_supervisor_candidate.yaml"
    )
    result = load_native_bdd(path.read_text())
    assert result.extracted_count == 13
    assert result.findings == ()


def test_invalid_entry_skips_are_explicit():
    result = load_native_bdd(source([None]))
    assert result.entry_skips == ((0, "invalid_entry"),)
    assert result.policies[-2].skip_reason == "invalid_id_values"


def test_duplicate_key_outside_scenario_is_still_boundary_failure():
    result = load_native_bdd("other: {a: 1, a: 2}\nspecification: {}\n")
    assert result.findings[0].code == "duplicate_yaml_key"
    assert all(p.skip_reason == "invalid_yaml_boundary" for p in result.policies)


def test_skipped_specs_are_recorded_without_affecting_result():
    from specification_core import TraceRecorder

    recorder = TraceRecorder()
    raw = source([])
    result = load_native_bdd(raw, recorder=recorder)
    assert len(recorder.events) == 6
    assert result == load_native_bdd(raw)
    assert [p.skip_reason for p in result.policies] == [
        None,
        None,
        "no_scenarios",
        "no_scenarios",
        "no_scenarios",
        None,
    ]


def test_unknown_profile_does_not_expose_path_in_events():
    result = load_native_bdd(source([]), profile="/private/example-secret")
    assert "/private/" not in repr(result.events)


def test_profile_selection_is_required_at_api_boundary():
    with pytest.raises(TypeError):
        native_load(source([]))
