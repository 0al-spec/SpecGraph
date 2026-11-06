"""Current-run custody and exact pinned scope must survive every stage."""

from specification_core import PredicateSpec

from .model import RunRecords, Stage, StageArtifact


def run_linkage(records: RunRecords) -> bool:
    pin, execution, collection, report = (
        records.pin,
        records.execution,
        records.collection,
        records.report,
    )
    finalization = records.finalization
    owner = records.owner

    def owned(artifact: StageArtifact | None, stage: Stage) -> bool:
        return bool(
            artifact
            and artifact.owner == owner
            and artifact.stage == stage
            and artifact.artifact_id
        )

    if not all((pin, execution, collection, report, finalization)):
        return False
    if any(item.owner != owner for item in (pin, execution, collection, report, finalization)):
        return False
    if not pin.sources_compatible or not finalization.inputs_unchanged:
        return False
    if execution.execution_revision != owner.request.scope.execution_revision:
        return False
    if not execution.producer_run_id or not execution.journals:
        return False
    artifacts = (*execution.journals, execution.binding_plan)
    if not all(owned(a, Stage.EXECUTE) for a in artifacts):
        return False
    if len({a.artifact_id for a in artifacts}) != len(artifacts):
        return False
    if len({a.file.path for a in artifacts}) != len(artifacts):
        return False
    return (
        collection.consumed_journals == execution.journals
        and collection.consumed_plan == execution.binding_plan
        and owned(collection.artifact, Stage.COLLECT)
        and report.consumed_collection == collection.artifact
        and owned(report.artifact, Stage.REPORT)
        and collection.artifact.file.path not in {a.file.path for a in artifacts}
        and report.artifact.file.path
        not in {
            *(a.file.path for a in artifacts),
            collection.artifact.file.path,
        }
    )


RUN_LINKAGE_SPEC: PredicateSpec[RunRecords] = PredicateSpec(
    run_linkage,
    name="verification.current_run_linkage",
)
