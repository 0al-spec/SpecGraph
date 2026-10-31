import type { CheckResult, ContextVerificationCase } from "./generated/pilot/types";
import { relations } from "./generated/pilot/refs";
import type { Requirement, Spec } from "./generated/sgcore/types";
import { classes as core, relations as coreRelations } from "./generated/sgcore/refs";

const specification = { $type: core.Spec.alias, id: "SG-SPEC-0072" } satisfies Spec;
const requirement = {
  $type: core.Requirement.alias, id: "SG72-OUTCOME-PRECEDENCE",
} satisfies Requirement;

export function contextCase(
  scenario: ContextVerificationCase & { id: string },
  checks: readonly CheckResult[],
  checkLinks: readonly { relation: string; from: string; to: string }[],
) {
  const links = [
    ...checkLinks,
    { relation: relations.caseValidatesRequirement.alias, from: scenario.id, to: requirement.id },
    { relation: coreRelations.definesRequirement.alias, from: specification.id, to: requirement.id },
  ];
  return { specification, requirement, scenario, checks, relations: links };
}
