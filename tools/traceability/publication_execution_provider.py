"""Read selected retained producer reports; never execute pytest, HTTP or source."""

import hashlib
import subprocess
from pathlib import Path, PurePosixPath

from intent_decision_review.sources import (
    MAX_BYTES,
    GitSources,
    encoded,
    git,
    normalized_path,
    strict_json,
)
from publication_evidence.bound_observation_spec import TEST_OBSERVATION_SPEC
from publication_evidence.context import (
    ExecutionIdentity,
    SnapshotContext,
    SourceIdentity,
    TestObservationContext,
    TestSuiteContext,
)
from publication_evidence.snapshot_spec import SOURCE_SNAPSHOT_SPEC
from publication_evidence.suite_spec import TEST_SUITE_SPEC

from .evidence import (
    EvidenceDiagnostic,
    EvidenceRequest,
    NodeEvidence,
    ProviderEvidence,
    ProviderIdentity,
    SourceEvidence,
)
from .execution import (
    ExecutionBindingFacts,
    ExecutionEvidence,
    ExecutionSignal,
    RetainedExecutionArtifact,
    RetainedRuntimeBindingFacts,
)
from .execution_binding_spec import EXECUTION_BINDING_SPEC
from .publication import PROFILE, mapping, records, text
from .retained_runtime_binding_spec import RETAINED_RUNTIME_BINDING_SPEC

BINDINGS = "tools/feature_passports/static-publication-bindings.json"


def execution_identity(value: object) -> ExecutionIdentity:
    row = mapping(value, "execution identity")
    fields = tuple(row.get(key, "") for key in ("provider", "run_id", "run_attempt", "uri"))
    if not all(isinstance(v, str) for v in fields):
        raise ValueError("execution identity fields must be text")
    return ExecutionIdentity(*fields)


def source_identity(value: object) -> SourceIdentity:
    row = mapping(value, "source identity")
    files = mapping(row.get("files_sha256"), "source hashes")
    return SourceIdentity(
        text(row.get("repository"), "source repository"),
        text(row.get("revision"), "source revision"),
        tuple(sorted((normalized_path(p), text(h, "source hash")) for p, h in files.items())),
    )


def obligations(value: object) -> tuple[tuple[str, str], ...]:
    return tuple(
        (text(item.get("criterion_id"), "criterion ID"), text(item.get("test"), "test selector"))
        for item in records(value, "obligations")
    )


def pinned_source(
    request: EvidenceRequest,
) -> tuple[SourceIdentity, tuple[tuple[str, str], ...], str]:
    root, rev = request.repository_root, request.scope.source_revision
    sources = GitSources(root, rev, rev)
    bindings = mapping(strict_json(sources.blob(rev, BINDINGS)), "publication bindings")
    if (
        bindings.get("spec") != "specs/nodes/SG-SPEC-0071.yaml"
        or type(bindings.get("schema_version")) is not int
        or bindings["schema_version"] != 1
    ):
        raise ValueError("unsupported publication binding cohort/schema")
    expected = obligations(bindings.get("obligations"))
    package_files = {
        p.decode()
        for p in git(
            root, "ls-tree", "-rz", "--name-only", rev, "--", "tools/publication_evidence"
        ).split(b"\0")
        if p
        and PurePosixPath(p.decode()).parent.as_posix() == "tools/publication_evidence"
        and p.endswith(b".py")
    }
    paths = {
        BINDINGS,
        bindings["passport"],
        bindings["spec"],
        bindings["implementation"],
        "tools/publication_delivery_evidence.py",
        "tools/artifact_json.py",
        *package_files,
        *(selector.split("::", 1)[0] for _, selector in expected),
    }
    files = tuple(
        (path, hashlib.sha256(sources.blob(rev, path)).hexdigest()) for path in sorted(paths)
    )
    return (
        SourceIdentity(request.scope.repository_id, rev, files),
        expected,
        text(bindings.get("runtime_base_url"), "runtime origin"),
    )


def test_signal(
    report: dict,
    expected_source: SourceIdentity,
    expected_run: ExecutionIdentity,
    expected_obligations: tuple[tuple[str, str], ...],
    observer: object,
) -> ExecutionSignal:
    rows = records(report.get("obligations"), "test observations")
    declared = text(report.get("result"), "test result")
    matched = TEST_OBSERVATION_SPEC.is_satisfied_by(
        TestObservationContext(
            expected_source,
            expected_source,
            expected_run,
            execution_identity(observer),
            expected_obligations,
            obligations(rows),
        )
    )
    exit_code = report.get("exit_code")
    if type(exit_code) is not int:
        raise ValueError("pytest exit code must be an integer")
    result = (
        TEST_SUITE_SPEC.decide(
            TestSuiteContext(
                exit_code,
                frozenset(text(r.get("result"), "test case result") for r in rows),
                len(rows),
                len(expected_obligations),
                declared,
            )
        ).value
        if matched
        else None
    )
    return ExecutionSignal("tests", declared, "matched" if matched else "mismatch", result)


def bundle_identity(value: object) -> tuple[str, str]:
    row = mapping(value, "bundle identity")
    return tuple(
        text(row.get(key), "bundle hash") for key in ("manifest_sha256", "checksums_sha256")
    )


def delivery_signals(
    report: dict,
    run: ExecutionIdentity,
    source: SourceIdentity,
    expected_obligations: tuple[tuple[str, str], ...],
    origin: str,
) -> tuple[ExecutionSignal, ...]:
    stages = mapping(report.get("stages"), "delivery stages")
    signals = []
    for name in ("tests", "deploy", "runtime"):
        row = mapping(stages.get(name), f"delivery stage {name}")
        result = text(row.get("result"), "stage outcome")
        provenance = mapping(row.get("provenance"), "stage provenance")
        observer = provenance.get("observer")
        if observer is None and result == "missing":
            status = "not_asserted"
        else:
            matched = EXECUTION_BINDING_SPEC.is_satisfied_by(
                ExecutionBindingFacts(source.repository, run, execution_identity(observer))
            )
            if name == "tests":
                matched = matched and TEST_OBSERVATION_SPEC.is_satisfied_by(
                    TestObservationContext(
                        source,
                        source,
                        run,
                        execution_identity(observer),
                        expected_obligations,
                        obligations(row.get("obligations")),
                    )
                )
            else:
                # Both deploy/runtime describe the same retained HTTP observation.
                runtime = mapping(
                    mapping(stages.get("runtime"), "runtime stage").get("observation"),
                    "native HTTP observation",
                )
                execution = mapping(runtime.get("execution_context"), "native execution")
                if (
                    runtime.get("artifact_kind")
                    != "specgraph_static_artifact_remote_verification_report"
                    or type(runtime.get("schema_version")) is not int
                    or runtime["schema_version"] != 1
                ):
                    raise ValueError("unsupported native HTTP report")
                matched = matched and RETAINED_RUNTIME_BINDING_SPEC.is_satisfied_by(
                    RetainedRuntimeBindingFacts(
                        source.revision,
                        execution.get("source_revision", ""),
                        ExecutionBindingFacts(
                            source.repository, run, execution_identity(execution)
                        ),
                        bundle_identity(report.get("bundle_identity")),
                        bundle_identity(runtime.get("bundle_identity")),
                        origin,
                        text(runtime.get("remote_base_url"), "runtime origin"),
                    )
                )
            status = "matched" if matched else "mismatch"
        signals.append(ExecutionSignal(name, result, status))
    return tuple(signals)


class PublicationExecutionEvidenceProvider:
    provider_id = "publication.execution"
    version = "1.0.0"

    def identity(self) -> ProviderIdentity:
        tools = Path(__file__).resolve().parents[1]
        paths = (
            "traceability/publication_execution_provider.py",
            "traceability/execution.py",
            "traceability/execution_binding_spec.py",
            "traceability/evidence.py",
            "traceability/retained_runtime_binding_spec.py",
            "traceability/snapshot.py",
            "traceability/providers.py",
            "traceability/publication.py",
            "publication_trace_snapshot.py",
            "intent_decision_review/sources.py",
            "publication_evidence/context.py",
            "publication_evidence/bound_observation_spec.py",
            "publication_evidence/snapshot_spec.py",
            "publication_evidence/suite_spec.py",
        )
        return ProviderIdentity(
            self.provider_id,
            self.version,
            "specgraph.publication-retained-execution/v1",
            tuple((p, hashlib.sha256((tools / p).read_bytes()).hexdigest()) for p in paths),
        )

    def collect(self, request: EvidenceRequest) -> ProviderEvidence:
        selection = request.execution_selection
        if request.scope.resolver_profile != PROFILE or request.scope.spec_ids != ("SG-SPEC-0071",):
            raise ValueError(
                "publication execution requires the explicit SG-SPEC-0071 exact-links cohort"
            )
        if selection is None or request.artifact_paths:
            raise ValueError("publication execution requires typed explicit report/run selection")
        if not EXECUTION_BINDING_SPEC.is_satisfied_by(
            ExecutionBindingFacts(
                request.scope.repository_id, selection.identity, selection.identity
            )
        ):
            raise ValueError(
                "select a complete GitHub Actions run identity; local-run is ambiguous"
            )
        diagnostics, sources, artifacts = [], [], []
        try:
            expected_source, expected_obligations, origin = pinned_source(request)
        except (ValueError, TypeError, KeyError, OSError, subprocess.CalledProcessError):
            expected_source, expected_obligations, origin = None, (), ""
            diagnostics.append(EvidenceDiagnostic("execution_source_unavailable"))
        for role, path in (
            ("tests", selection.tests_report),
            ("delivery", selection.delivery_report),
        ):
            if path is None:
                continue
            raw, payload_json, signals = None, None, ()
            status = "unavailable"
            try:
                if not path.is_file():
                    raise ValueError("selected execution input must be a regular file")
                with path.open("rb") as stream:
                    raw = stream.read(MAX_BYTES + 1)
                report = mapping(strict_json(raw), "retained report")
                payload_json = encoded(report).encode()
                kind = (
                    "specgraph_publication_test_observation"
                    if role == "tests"
                    else "feature_delivery_signals"
                )
                if (
                    report.get("artifact_kind") != kind
                    or type(report.get("schema_version")) is not int
                    or report["schema_version"] != 1
                    or (
                        role == "delivery" and report.get("profile") != "linked_delivery_signals_v1"
                    )
                ):
                    raise ValueError("unsupported retained report kind/schema/profile")
                observed_source = source_identity(report.get("source"))
                observed_run = execution_identity(report.get("provenance"))
                matched = (
                    expected_source is not None
                    and SOURCE_SNAPSHOT_SPEC.is_satisfied_by(
                        SnapshotContext(expected_source, observed_source)
                    )
                    and EXECUTION_BINDING_SPEC.is_satisfied_by(
                        ExecutionBindingFacts(
                            request.scope.repository_id, selection.identity, observed_run
                        )
                    )
                )
                status = (
                    "unavailable"
                    if expected_source is None
                    else "matched"
                    if matched
                    else "mismatch"
                )
                if role == "tests" and expected_source is not None:
                    signal = test_signal(
                        report,
                        expected_source,
                        selection.identity,
                        expected_obligations,
                        report.get("provenance"),
                    )
                    signals = (signal,)
                    if not matched:
                        signals = (ExecutionSignal("tests", signal.producer_result, status),)
                    elif signal.binding_status != "matched":
                        status = "mismatch"
                elif role == "delivery" and expected_source is not None:
                    signals = delivery_signals(
                        report, selection.identity, expected_source, expected_obligations, origin
                    )
                    if not matched:
                        signals = tuple(
                            ExecutionSignal(s.stage, s.producer_result, "mismatch") for s in signals
                        )
                if status == "mismatch":
                    diagnostics.append(EvidenceDiagnostic("execution_scope_mismatch", owner=role))
                for signal in signals:
                    if signal.binding_status == "mismatch":
                        diagnostics.append(
                            EvidenceDiagnostic(
                                "execution_signal_mismatch", owner=f"{role}.{signal.stage}"
                            )
                        )
            except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError):
                status = "unavailable"
                diagnostics.append(EvidenceDiagnostic("execution_artifact_unavailable", owner=role))
            # Hash original selected bytes; retain parsed producer data without rewriting outcomes.
            sources.append(
                SourceEvidence(
                    f"artifact:{role}",
                    "read" if raw is not None else "unavailable",
                    hashlib.sha256(raw).hexdigest()
                    if raw is not None and len(raw) <= MAX_BYTES
                    else None,
                    None if status == "matched" else status,
                )
            )
            artifacts.append(RetainedExecutionArtifact(role, status, signals, payload_json))
        node = NodeEvidence("SG-SPEC-0071", (), (), False, False, tuple(diagnostics))
        return ProviderEvidence(
            self.identity(),
            request.scope,
            (node,),
            tuple(sources),
            execution=ExecutionEvidence(selection.identity, tuple(artifacts)),
        )
