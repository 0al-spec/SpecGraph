"""Nested observation facts must agree; successful observations must be complete."""

from specification_core import PredicateSpec

from .collection_context import CollectedCriterion


def consistent_observation(context: CollectedCriterion) -> bool:
    row = context.row
    observation = row.observation
    if observation is None:
        return row.observed_outcome != "passed"
    if len(row.bindings) != 1:
        return False
    # C2c propagates these findings before computing the row outcome.
    if not set(observation.findings) <= set(row.findings):
        return False
    if observation.will_be_retried is True or (
        observation.case_finished and observation.will_be_retried is not False
    ):
        return False
    statuses = dict(observation.case_step_statuses)
    if len(statuses) != len(observation.case_step_statuses) or not all(statuses):
        return False
    if tuple(step.assertion for step in observation.steps) != row.bindings[0].assertions:
        return False
    if any(
        step.assertion.step_id not in statuses
        or step.producer_status != statuses[step.assertion.step_id]
        for step in observation.steps
    ):
        return False
    return row.observed_outcome != "passed" or (
        observation.case_finished
        and bool(observation.run_success)
        and all(step.measurement_json is not None for step in observation.steps)
    )


COLLECTION_OBSERVATION_SPEC: PredicateSpec[CollectedCriterion] = PredicateSpec(
    consistent_observation,
    name="verification.collection_observation_consistency",
)
