import type { CheckResult, ContextVerificationCase } from "./generated/pilot/types";
import { classes, relations } from "./generated/pilot/refs";
import { contextCase } from "./case-model";

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
];

export const model = contextCase(scenario, checks, links);
