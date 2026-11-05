"""Read-only adapter for the supported retained Cucumber Messages profile."""

from collections import defaultdict

from intent_decision_review.sources import encoded, strict_json

from .criterion import (
    AttemptObservation,
    CriterionBinding,
    CriterionFinding,
    FindingKind,
    JournalDeclaration,
    StepObservation,
)
from .criterion_inputs import canonical_json
from .evidence import AgreementFacts
from .fact_agreement_spec import FACT_AGREEMENT_SPEC
from .publication import mapping, records, text

PROTOCOL_VERSION = "34.2.1"
STATUSES = frozenset(
    {"AMBIGUOUS", "FAILED", "PASSED", "PENDING", "SKIPPED", "UNDEFINED", "UNKNOWN"}
)
KEYS = {
    "meta": (),
    "testRunStarted": (),
    "testRunFinished": (),
    "source": ("uri",),
    "pickle": ("id",),
    "testCase": ("id",),
    "testCaseStarted": ("id",),
    "testCaseFinished": ("testCaseStartedId",),
    "testStepFinished": ("testCaseStartedId", "testStepId"),
    "attachment": ("testCaseStartedId", "testStepId", "mediaType"),
}


class JournalFinding(ValueError):
    def __init__(self, kind: FindingKind, code: str, detail: str = "") -> None:
        self.finding = CriterionFinding(kind, code, detail)
        super().__init__(detail or code)


class CucumberMessages:
    def __init__(self, groups: dict[tuple[str, tuple[str, ...]], dict[str, dict]]) -> None:
        self._groups = groups

    @classmethod
    def parse(cls, raw: bytes) -> "CucumberMessages":
        raw.decode("utf-8")
        if b"\0" in raw:
            raise ValueError("journal must be UTF-8 NDJSON")
        groups = defaultdict(dict)
        for line in raw.splitlines():
            envelope = mapping(strict_json(line), "Cucumber envelope")
            if len(envelope) != 1:
                raise ValueError("Cucumber envelope must contain exactly one message")
            kind, value = next(iter(envelope.items()))
            if kind not in KEYS:
                continue  # The profile does not interpret Gherkin AST, hooks or step definitions.
            message = mapping(value, f"Cucumber {kind}")
            if kind == "attachment" and not all(k in message for k in KEYS[kind]):
                continue  # Unscoped attachments cannot participate in criterion evidence.
            key = tuple(text(message.get(k), f"Cucumber {kind}.{k}") for k in KEYS[kind])
            groups[kind, key][canonical_json(message)] = message
        return cls(dict(groups))

    def message(self, kind: str, *key: str, optional: bool = False) -> dict | None:
        variants = self._groups.get((kind, key), {})
        label = f"{kind}({', '.join(key)})"
        if not variants:
            if optional:
                return None
            raise JournalFinding("unavailable", "journal_record_missing", label)
        if not FACT_AGREEMENT_SPEC.is_satisfied_by(AgreementFacts(frozenset(variants))):
            raise JournalFinding("conflict", "journal_records_disagree", label)
        return next(iter(variants.values()))

    def matching_ids(self, kind: str, field: str, expected: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                key[0]
                for (entry_kind, key), variants in self._groups.items()
                if entry_kind == kind
                and any(row.get(field) == expected for row in variants.values())
            )
        )

    def check_case_start(self, binding: CriterionBinding) -> None:
        if binding.attempt != 0:
            raise JournalFinding("unavailable", "retry_unsupported")
        selected = self.message("testCaseStarted", binding.case_started_id, optional=True)
        # Inspect every start for the selected case, including retries with a different start ID.
        case_starts = self.matching_ids("testCaseStarted", "testCaseId", binding.case_id)
        for started_id in case_starts:
            attempt = self.message("testCaseStarted", started_id).get("attempt")
            if type(attempt) is not int or attempt < 0:
                raise ValueError("Cucumber attempt must be a nonnegative integer")
            if attempt != 0:
                raise JournalFinding("unavailable", "retry_unsupported")
        if len(case_starts) > 1:
            raise JournalFinding("conflict", "ambiguous_case_start", binding.case_id)
        if selected is None:
            if case_starts:
                raise ValueError("selected case start ID does not identify the recorded attempt")
            raise JournalFinding("unavailable", "case_start_missing", binding.case_started_id)
        if selected.get("testCaseId") != binding.case_id:
            raise ValueError("selected case start belongs to a different case")

    def run_success(self, declaration: JournalDeclaration) -> bool | None:
        run = self.message("testRunStarted")
        if run.get("id") != declaration.run_id:
            raise ValueError("journal start ID does not match the selected run")
        finished = self.message("testRunFinished", optional=True)
        if finished is None:
            return None
        if finished.get("testRunStartedId") != declaration.run_id:
            raise ValueError("journal finish belongs to a different run")
        if type(finished.get("success")) is not bool:
            raise ValueError("Cucumber run finish success must be Boolean")
        return finished["success"]

    def observe(
        self,
        declaration: JournalDeclaration,
        binding: CriterionBinding,
        scenario: str,
        feature: str,
    ) -> AttemptObservation:
        if self.message("meta").get("protocolVersion") != PROTOCOL_VERSION:
            raise JournalFinding("unavailable", "unsupported_cucumber_version")
        run_success = self.run_success(declaration)
        self.check_case_start(binding)
        case = self.message("testCase", binding.case_id, optional=True)
        if case is None:
            if any(kind == "testCase" for kind, _ in self._groups):
                raise ValueError("selected case ID is foreign to this journal")
            raise JournalFinding("unavailable", "case_missing", binding.case_id)
        if case.get("testRunStartedId") != declaration.run_id:
            raise ValueError("test case does not belong to the selected run")
        pickle_id = text(case.get("pickleId"), "pickle ID")
        pickle = self.message("pickle", pickle_id)
        if self.matching_ids("testCase", "pickleId", pickle_id) != (binding.case_id,):
            raise JournalFinding("conflict", "ambiguous_case_for_pickle", pickle_id)
        uri = declaration.feature.path
        tags = {
            text(t.get("name"), "pickle tag") for t in records(pickle.get("tags"), "pickle tags")
        }
        if pickle.get("uri") != uri or f"@specgraph-id={scenario}" not in tags:
            raise ValueError("pickle does not match the selected feature/scenario")
        if self.message("source", uri).get("data") != feature:
            raise ValueError("journal feature source differs from pinned Git source")

        finished = self.message("testCaseFinished", binding.case_started_id, optional=True)
        will_retry = None if finished is None else finished.get("willBeRetried")
        if finished is not None and type(will_retry) is not bool:
            raise ValueError("Cucumber case finish willBeRetried must be Boolean")
        if will_retry:
            raise JournalFinding("unavailable", "retry_unsupported")

        findings = []
        if run_success is None:
            findings.append(CriterionFinding("unavailable", "run_unfinished"))
        if finished is None:
            findings.append(CriterionFinding("unavailable", "case_unfinished"))
        test_steps = unique_rows(records(case.get("testSteps"), "case steps"), "case step")
        pickle_steps = unique_rows(records(pickle.get("steps"), "pickle steps"), "pickle step")
        linked = [
            text(step["pickleStepId"], "linked pickle step ID")
            for step in test_steps.values()
            if "pickleStepId" in step
        ]
        if len(linked) != len(pickle_steps) or set(linked) != pickle_steps.keys():
            raise ValueError("test case steps do not identify the complete pickle step inventory")

        statuses = {}
        for step_id in sorted(test_steps):
            try:
                statuses[step_id] = self.step_status(binding.case_started_id, step_id)
            except JournalFinding as error:
                findings.append(error.finding)
                statuses[step_id] = None
            except ValueError as error:
                findings.append(CriterionFinding("invalid", "step_result_invalid", str(error)))
                statuses[step_id] = None
        unknown_steps = {
            key[1]
            for kind, key in self._groups
            if kind == "testStepFinished" and key[0] == binding.case_started_id
        } - test_steps.keys()
        if unknown_steps:
            findings.append(
                CriterionFinding("invalid", "foreign_step_result", ", ".join(sorted(unknown_steps)))
            )

        steps = []
        for expected in binding.assertions:
            step = test_steps.get(expected.step_id)
            if step is None or step.get("pickleStepId") not in pickle_steps:
                findings.append(CriterionFinding("invalid", "foreign_assertion_step", expected.id))
                steps.append(StepObservation(expected))
                continue
            pickle_step_id = step["pickleStepId"]
            step_text = text(pickle_steps[pickle_step_id].get("text"), "pickle step text")
            measurement = None
            try:
                measurement = self.measurement(
                    binding.case_started_id, expected.step_id, expected.media_type
                )
            except JournalFinding as error:
                findings.append(error.finding)
            except ValueError as error:
                findings.append(CriterionFinding("invalid", "measurement_invalid", str(error)))
            steps.append(
                StepObservation(
                    expected, pickle_step_id, step_text, statuses[expected.step_id], measurement
                )
            )
        return AttemptObservation(
            pickle_id,
            run_success,
            finished is not None,
            will_retry,
            tuple(statuses.items()),
            tuple(steps),
            tuple(sorted(set(findings))),
        )

    def step_status(self, started_id: str, step_id: str) -> str:
        message = self.message("testStepFinished", started_id, step_id)
        result = mapping(message.get("testStepResult"), "Cucumber step result")
        status = text(result.get("status"), "Cucumber step status")
        if status not in STATUSES:
            raise JournalFinding("unavailable", "unsupported_step_status", status)
        return status

    def measurement(self, started_id: str, step_id: str, media_type: str) -> str:
        message = self.message("attachment", started_id, step_id, media_type)
        if message.get("contentEncoding") != "IDENTITY":
            raise JournalFinding("unavailable", "unsupported_attachment_encoding")
        body = message.get("body")
        if not isinstance(body, str):
            raise ValueError("JSON attachment body must be text")
        return canonical_json(mapping(strict_json(body.encode()), "observed measurement"))


def unique_rows(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        row_id = text(row.get("id"), f"{label} ID")
        if row_id in result and encoded(row) != encoded(result[row_id]):
            raise JournalFinding("conflict", "journal_records_disagree", f"{label}({row_id})")
        result[row_id] = row
    return result
