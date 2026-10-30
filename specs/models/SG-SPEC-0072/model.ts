import type { CheckResult, ContextVerificationCase } from "./generated/pilot/types";
import { classes, relations } from "./generated/pilot/refs";
import type { Requirement, Spec } from "./generated/sgcore/types";
import { classes as core, relations as coreRelations } from "./generated/sgcore/refs";

// Hypothetical test declarations. Actual execution is reported separately.
const specification = { $type: core.Spec.alias, id: "SG-SPEC-0072" } satisfies Spec;
const requirement = {
  $type: core.Requirement.alias, id: "SG72-OUTCOME-PRECEDENCE",
} satisfies Requirement;
const scenario = {
  $type: classes.ContextVerificationCase.alias, id: "SG72-MIXED",
  expectedOutcome: "invalid",
} satisfies ContextVerificationCase;
const checks = [
  {
    $type: classes.CheckResult.alias, id: "duplicate-selection",
    check: "selection", outcome: "invalid",
    detail: "duplicate package identity or namespace",
  },
  {
    $type: classes.CheckResult.alias, id: "missing-compiler",
    check: "compiler", outcome: "unavailable",
    detail: "operator-provided executable is unavailable",
  },
] satisfies readonly CheckResult[];
const links = [
  { relation: relations.caseIncludesCheck.alias, from: scenario.id, to: "duplicate-selection" },
  { relation: relations.caseIncludesCheck.alias, from: scenario.id, to: "missing-compiler" },
  { relation: relations.caseValidatesRequirement.alias, from: scenario.id, to: requirement.id },
  { relation: coreRelations.definesRequirement.alias, from: specification.id, to: requirement.id },
];

export const model = { specification, requirement, scenario, checks, relations: links } as const;
