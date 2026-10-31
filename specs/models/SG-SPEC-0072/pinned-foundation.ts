import type { CheckResult, ContextVerificationCase } from "./generated/pilot/types";
import { classes, relations } from "./generated/pilot/refs";
import { contextCase } from "./case-model";

const scenario = {
  $type: classes.ContextVerificationCase.alias, id: "SG72-PINNED-FOUNDATION",
  expectedOutcome: "verified",
} satisfies ContextVerificationCase;
const checks = [
  {
    $type: classes.CheckResult.alias, id: "captured-member",
    check: "member_capture", outcome: "verified",
    detail: "source, IR and package identity checked",
  },
  {
    $type: classes.CheckResult.alias, id: "foundation-closure",
    check: "dependency_closure", outcome: "verified",
    detail: "Pinned foundation vocabulary and qualified references checked",
  },
] satisfies readonly CheckResult[];
const links = [
  { relation: relations.caseIncludesCheck.alias, from: scenario.id, to: "captured-member" },
  { relation: relations.caseIncludesCheck.alias, from: scenario.id, to: "foundation-closure" },
  { relation: relations.closureUsesMemberCheck.alias, from: "foundation-closure", to: "captured-member" },
];

export const model = contextCase(scenario, checks, links);
