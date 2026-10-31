import payloadCase from "./case.json";
import manifestCase from "./manifest-case.json";
import { classes as core, relations as trace } from "./generated/core/refs";
import type { AcceptanceCriterion, Requirement, Test } from "./generated/core/types";
import { classes, relations } from "./generated/payload/refs";
import type { FetchedFileObservation, LocalManifest, ManifestEntry } from "./generated/payload/types";

interface ComparisonCase {
  source: typeof payloadCase.source;
  observations: Readonly<Record<string, { observedSHA256: string }>>;
}

function comparisonModel(example: ComparisonCase, target: (ManifestEntry | LocalManifest) & { id: string }) {
  const { source } = example;
  const requirement = { $type: core.Requirement.alias, id: source.requirement } satisfies Requirement;
  const criterion = { $type: core.AcceptanceCriterion.alias, id: source.criterion } satisfies AcceptanceCriterion;
  const test = { $type: core.Test.alias, id: source.test } satisfies Test;
  const observations = Object.entries(example.observations).map(([id, input]) => ({
    $type: classes.FetchedFileObservation.alias, id, observedSHA256: input.observedSHA256,
  } satisfies FetchedFileObservation));

  return {
    nodes: [requirement, criterion, test, target, ...observations],
    edges: [
      { relation: trace.requirementValidatedByCriterion.alias, from: requirement.id, to: criterion.id },
      { relation: trace.testValidatesRequirement.alias, from: test.id, to: requirement.id },
      ...observations.flatMap(o => [
        { relation: relations.comparedAgainst.alias, from: o.id, to: target.id },
        { relation: trace.evidenceSupportsCriterion.alias, from: o.id, to: criterion.id },
      ]),
    ],
  };
}

export const models = {
  "PB-PAYLOAD": comparisonModel(payloadCase, {
    $type: classes.ManifestEntry.alias, id: payloadCase.manifestEntry.path, ...payloadCase.manifestEntry,
  }),
  "PB-MANIFEST": comparisonModel(manifestCase, {
    $type: classes.LocalManifest.alias, id: manifestCase.localManifest.path, ...manifestCase.localManifest,
  }),
};
