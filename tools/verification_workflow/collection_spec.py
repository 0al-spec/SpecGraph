"""Bind retained C2c facts to the requested passport, inventory and fresh outputs."""

from specification_core import PredicateSpec

from traceability.criterion_provider import criterion_row

from .model import ExpectedMeasurement, RunRecords, Stage


def collection_scope(records: RunRecords) -> bool:
    collection, execution = records.collection, records.execution
    if collection is None or execution is None or collection.evidence is None:
        return False
    evidence = collection.evidence
    request = records.owner.request
    scope = request.scope
    selected = next(s for s in request.definition.steps if s.stage == Stage.COLLECT)
    adapter = next(
        o.adapter for o in request.registry.operations if o.identity == selected.operation_id
    )
    if collection.provider != adapter or evidence.passport != scope.passport.identity:
        return False
    selection = evidence.selection
    if (
        (selection.workspace, selection.spec, selection.passport)
        != (
            scope.workspace,
            scope.spec,
            scope.passport.artifact,
        )
        or execution.binding_plan is None
        or selection.plan != execution.binding_plan.file
    ):
        return False
    journals = {a.artifact_id: a.file for a in execution.journals}
    if dict(selection.journals) != journals or len(selection.journals) != len(journals):
        return False
    if len(evidence.declared_journals) != len(journals):
        return False
    declarations = {j.artifact_id: j for j in evidence.declared_journals}
    if set(declarations) != set(journals):
        return False
    if any(
        (j.sha256, j.run_id, j.test_source_revision, j.execution_source_revision)
        != (
            journals[j.artifact_id].sha256,
            execution.producer_run_id,
            scope.test_revision,
            scope.execution_revision,
        )
        for j in declarations.values()
    ):
        return False
    if evidence.findings or evidence.unmatched_bindings:
        return False
    if tuple(row.source for row in evidence.rows) != tuple(t.source for t in scope.criteria):
        return False
    for row, target in zip(evidence.rows, scope.criteria, strict=True):
        # Reuse C2c's pure projection: a caller cannot relabel failed facts as passed.
        projected = criterion_row(
            row.source,
            row.bindings,
            list(row.findings),
            row.journal,
            row.observation,
        )
        if (row.binding_integrity, row.observed_outcome) != (
            projected.binding_integrity,
            projected.observed_outcome,
        ):
            return False
        if len(row.bindings) != 1 or row.journal is None:
            return False
        binding = row.bindings[0]
        if (
            binding.pointer,
            binding.criterion_id,
            binding.contract_ref_id,
            binding.passport_binding_id,
        ) != (
            target.source.pointer,
            target.criterion_id,
            target.contract_ref_id,
            target.passport_binding_id,
        ) or row.journal != declarations.get(binding.artifact_id):
            return False
        try:
            expectations = tuple(
                ExpectedMeasurement(a.id, a.media_type, a.expected_json) for a in binding.assertions
            )
        except (ValueError, TypeError):
            return False
        if expectations != target.expectations or binding.attempt != 0:
            return False
        observation = row.observation
        if observation is not None:
            # C2c propagates these findings to the row before projecting its outcome.
            if not set(observation.findings) <= set(row.findings):
                return False
            if observation.will_be_retried is True or (
                observation.case_finished and observation.will_be_retried is not False
            ):
                return False
            statuses = dict(observation.case_step_statuses)
            if len(statuses) != len(observation.case_step_statuses) or not all(statuses):
                return False
            if tuple(step.assertion for step in observation.steps) != binding.assertions:
                return False
            if any(
                step.assertion.step_id not in statuses
                or step.producer_status != statuses[step.assertion.step_id]
                for step in observation.steps
            ):
                return False
        if row.observed_outcome == "passed":
            if observation is None or not observation.case_finished or not observation.run_success:
                return False
            if any(step.measurement_json is None for step in observation.steps):
                return False
    return True


COLLECTION_SCOPE_SPEC: PredicateSpec[RunRecords] = PredicateSpec(
    collection_scope,
    name="verification.collection_passport_scope",
)
