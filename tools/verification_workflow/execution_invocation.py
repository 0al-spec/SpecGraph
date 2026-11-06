"""Neutral invocation challenge with a bounded Cucumber Messages emission transport.

The runner receives the reserved environment value before execution. A Before
hook must attach that exact JSON value (IDENTITY encoding and MEDIA_TYPE) inside
each selected case, between its step start and finish. The operation only reads
these original bytes; neither the binder nor a post-processing formatter may
insert the marker. A producer run ID is joined via Cucumber identities and need
not equal the workflow run ID. This detects cached-output mistakes; a malicious
producer that fabricates an entire journal remains outside local custody.
"""

import json
from dataclasses import replace

from intent_decision_review.sources import strict_json
from traceability.criterion_inputs import fields
from traceability.cucumber_messages import CucumberMessages
from traceability.publication import mapping, records, text

from .execution_invocation_spec import EXECUTION_INVOCATION_SPEC, InvocationEmission
from .execution_model import BoundRun, InvocationIdentity, ProducerCommand

INVOCATION_ENV = "SPECGRAPH_VERIFICATION_INVOCATION"
MEDIA_TYPE = "application/vnd.specgraph.execution-invocation+json"


def invocation_command(command: ProducerCommand, invocation: InvocationIdentity) -> ProducerCommand:
    if INVOCATION_ENV in dict(command.environment):
        raise ValueError("producer cannot override the runtime invocation challenge")
    value = json.dumps(invocation.to_payload(), sort_keys=True)
    return replace(command, environment=(*command.environment, (INVOCATION_ENV, value)))


def position(envelopes: tuple[dict, ...], kind: str, **identity: str) -> int:
    indices = [
        index
        for index, envelope in enumerate(envelopes)
        if kind in envelope
        and all(mapping(envelope[kind], kind).get(k) == v for k, v in identity.items())
    ]
    if len(indices) != 1:
        raise ValueError(f"invocation requires one unambiguous {kind} event")
    return indices[0]


def validate_invocation(raw: bytes, bound: BoundRun, invocation: InvocationIdentity) -> None:
    journal = CucumberMessages.parse(raw)
    envelopes = tuple(
        mapping(strict_json(line), "invocation envelope") for line in raw.splitlines()
    )
    if journal.message("testRunStarted").get("id") != bound.producer_run_id:
        raise ValueError("invocation producer run differs from the selected journal")
    run_start = position(envelopes, "testRunStarted", id=bound.producer_run_id)
    cases = {(row.case_id, row.case_started_id) for row in bound.criteria}
    if not cases:
        raise ValueError("invocation has no selected executed case")
    for case_id, started_id in sorted(cases):
        case = journal.message("testCase", case_id)
        start = journal.message("testCaseStarted", started_id)
        if (
            case.get("testRunStartedId") != bound.producer_run_id
            or start.get("testCaseId") != case_id
        ):
            raise ValueError("invocation case does not join the selected producer run")
        markers = [
            (i, envelope["attachment"])
            for i, envelope in enumerate(envelopes)
            if envelope.get("attachment", {}).get("testCaseStartedId") == started_id
            and envelope["attachment"].get("mediaType") == MEDIA_TYPE
        ]
        if len(markers) != 1:
            raise ValueError("invocation requires exactly one emitted challenge per selected case")
        index, marker = markers[0]
        validate_marker(envelopes, case, started_id, run_start, index, marker, invocation)


def validate_marker(
    envelopes: tuple[dict, ...],
    case: dict,
    started_id: str,
    run_start: int,
    index: int,
    marker: dict,
    invocation: InvocationIdentity,
) -> None:
    if marker.get("contentEncoding") != "IDENTITY":
        raise ValueError("invocation attachment requires IDENTITY encoding")
    payload = fields(
        strict_json(text(marker.get("body"), "invocation body")),
        "profile request_id workflow_run_id nonce",
        "invocation payload",
    )
    if payload["profile"] != "specgraph.execution-invocation/v1":
        raise ValueError("unsupported invocation profile")
    observed = InvocationIdentity(
        *(text(payload[key], key) for key in ("request_id", "workflow_run_id", "nonce"))
    )
    step_id = text(marker.get("testStepId"), "invocation step ID")
    if sum(step.get("id") == step_id for step in records(case.get("testSteps"), "case steps")) != 1:
        raise ValueError("invocation marker does not name one selected case step")
    step_identity = dict(testCaseStartedId=started_id, testStepId=step_id)
    facts = InvocationEmission(
        invocation,
        observed,
        run_start,
        position(envelopes, "testCaseStarted", id=started_id),
        position(envelopes, "testStepStarted", **step_identity),
        index,
        position(envelopes, "testStepFinished", **step_identity),
        position(envelopes, "testCaseFinished", testCaseStartedId=started_id),
    )
    if not EXECUTION_INVOCATION_SPEC.is_satisfied_by(facts):
        raise ValueError("invocation challenge mismatch or marker outside the executing step")
