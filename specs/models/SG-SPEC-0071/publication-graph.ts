import { classes as core, relations as trace } from "./generated/core/refs";
import type { AcceptanceCriterion, Requirement, Test } from "./generated/core/types";
import { classes, relations } from "./generated/payload/refs";
import type { FetchedFileObservation, LocalMetadataFile, ManifestEntry, PayloadNotFoundObservation } from "./generated/payload/types";

export type Observation = (FetchedFileObservation | PayloadNotFoundObservation) & { id: string };
export interface FileCheck {
  target: (ManifestEntry | LocalMetadataFile) & { id: string };
  observations: Observation[];
}

export function manifestEntry(entry: Pick<ManifestEntry, "path" | "expectedSHA256">) {
  return { $type: classes.ManifestEntry.alias, id: entry.path, ...entry } satisfies ManifestEntry;
}

export function notFoundObservation(id: string, input: { httpStatus: number }) {
  if (input.httpStatus !== 404 || "observedSHA256" in input || "body" in input) {
    throw new Error("PB-MISSING expects HTTP 404 without payload bytes or an observed digest");
  }
  return {
    $type: classes.PayloadNotFoundObservation.alias, id, httpStatus: input.httpStatus,
  } satisfies PayloadNotFoundObservation;
}

export function publicationGraph(
  source: { requirement: string; criterion: string; test: string },
  checks: FileCheck[],
) {
  const requirement = { $type: core.Requirement.alias, id: source.requirement } satisfies Requirement;
  const criterion = { $type: core.AcceptanceCriterion.alias, id: source.criterion } satisfies AcceptanceCriterion;
  const test = { $type: core.Test.alias, id: source.test } satisfies Test;
  return {
    nodes: [requirement, criterion, test, ...checks.flatMap(c => [c.target, ...c.observations])],
    edges: [
      { relation: trace.requirementValidatedByCriterion.alias, from: requirement.id, to: criterion.id },
      { relation: trace.testValidatesRequirement.alias, from: test.id, to: requirement.id },
      ...checks.flatMap(({ target, observations }) => observations.flatMap(o => [
        {
          relation: o.$type === classes.FetchedFileObservation.alias
            ? relations.comparedAgainst.alias
            : relations.requestedEntry.alias,
          from: o.id,
          to: target.id,
        },
        { relation: trace.evidenceSupportsCriterion.alias, from: o.id, to: criterion.id },
      ])),
    ],
  };
}
