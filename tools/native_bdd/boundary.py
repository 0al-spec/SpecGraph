"""Read-only YAML edge: original scalar types, exact source pin, no profile activation."""

from hashlib import sha256

import yaml

from spec_yaml import DuplicateKeyError, load_yaml_text

from .composition import POLICIES, evaluate
from .context import (
    BDDContext,
    BDDResult,
    BDDScenarioPresence,
    PolicyOutcome,
    ReferenceInput,
    ScenarioInput,
    TextInput,
)
from .policy import issue


def text(value: object) -> TextInput:
    return TextInput(value if isinstance(value, str) else None)


def entry(value: object) -> ScenarioInput:
    if not isinstance(value, dict):
        return ScenarioInput(False, text(None), False, text(None), False, (), ())
    steps = value.get("steps")
    return ScenarioInput(
        True,
        text(value.get("id")),
        "scenario" in value,
        text(value.get("scenario")),
        isinstance(steps, list),
        tuple(text(s) for s in steps) if isinstance(steps, list) else (),
        tuple(sorted(str(k) for k in value if k not in {"id", "scenario", "steps"})),
    )


def context(node: dict, profile: str) -> BDDContext:
    spec = node.get("specification", {})
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping")
    native = spec.get("bdd_scenarios")
    refs = []
    obs = spec.get("observability", {})
    if not isinstance(obs, dict):
        refs.append(ReferenceInput(text(None), "specification.observability"))
    else:
        obligations = obs.get("obligations", [])
        if not isinstance(obligations, list):
            refs.append(ReferenceInput(text(None), "specification.observability.obligations"))
        else:
            for i, obligation in enumerate(obligations):
                path = f"specification.observability.obligations[{i}]"
                if not isinstance(obligation, dict):
                    refs.append(ReferenceInput(text(None), path))
                    continue
                values = obligation.get("scenario_ids", [])
                if not isinstance(values, list):
                    refs.append(ReferenceInput(text(None), path + ".scenario_ids"))
                else:
                    refs.extend(
                        ReferenceInput(text(v), f"{path}.scenario_ids[{j}]")
                        for j, v in enumerate(values)
                    )
    return BDDContext(
        profile,
        "bdd_scenarios" in spec,
        "scenarios" in spec,
        isinstance(native, list),
        tuple(entry(e) for e in native) if isinstance(native, list) else (),
        tuple(refs),
    )


def load_native_bdd(source: str, *, profile: str, recorder=None) -> BDDResult:
    digest = sha256(source.encode("utf-8")).hexdigest()
    try:
        facts = context(load_yaml_text(source), profile)
    except (DuplicateKeyError, yaml.YAMLError, ValueError, TypeError) as error:
        code = "duplicate_yaml_key" if isinstance(error, DuplicateKeyError) else "invalid_value"
        if recorder is not None:
            for policy in POLICIES:
                recorder.skipped(policy.rule_ref)
        return BDDResult(
            profile,
            BDDScenarioPresence.INVALID,
            (issue(code, "document"),),
            tuple(PolicyOutcome(p.rule_ref, "skipped", "invalid_yaml_boundary") for p in POLICIES),
            (),
            digest,
        )
    return evaluate(facts, digest, recorder=recorder)
