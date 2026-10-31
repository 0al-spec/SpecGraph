import example from "./case.json";
import { classes as core, relations as trace } from "./generated/core/refs";
import type { AcceptanceCriterion, Requirement, Test } from "./generated/core/types";
import { classes, relations } from "./generated/payload/refs";
import type { ManifestEntry, PayloadObservation } from "./generated/payload/types";

const { source } = example;
const requirement = { $type: core.Requirement.alias, id: source.requirement } satisfies Requirement;
const criterion = { $type: core.AcceptanceCriterion.alias, id: source.criterion } satisfies AcceptanceCriterion;
const test = { $type: core.Test.alias, id: source.test } satisfies Test;
const entry = {
  $type: classes.ManifestEntry.alias, id: example.manifestEntry.path, ...example.manifestEntry,
} satisfies ManifestEntry;

// Each observation describes a separate fetch of the same manifest path.
const observations = Object.entries(example.observations).map(([id, input]) => ({
  $type: classes.PayloadObservation.alias, id, observedSHA256: input.observedSHA256,
} satisfies PayloadObservation));

export const model = {
  nodes: [requirement, criterion, test, entry, ...observations],
  edges: [
    { relation: trace.requirementValidatedByCriterion.alias, from: requirement.id, to: criterion.id },
    { relation: trace.testValidatesRequirement.alias, from: test.id, to: requirement.id },
    ...observations.flatMap(o => [
      { relation: relations.comparedAgainst.alias, from: o.id, to: entry.id },
      { relation: trace.evidenceSupportsCriterion.alias, from: o.id, to: criterion.id },
    ]),
  ],
};
