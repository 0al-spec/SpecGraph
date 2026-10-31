import payloadCase from "./case.json";
import manifestCase from "./manifest-case.json";
import checksumsCase from "./checksums-case.json";
import missingCase from "./missing-case.json";
import { classes as core, relations as trace } from "./generated/core/refs";
import type { AcceptanceCriterion, Requirement, Test } from "./generated/core/types";
import { classes, relations } from "./generated/payload/refs";
import type { FetchedFileObservation, LocalMetadataFile, ManifestEntry, PayloadNotFoundObservation } from "./generated/payload/types";

interface ComparisonCase {
  source: typeof payloadCase.source;
  observations: Readonly<Record<string, { observedSHA256: string }>>;
}

function fetchedObservations(example: ComparisonCase) {
  return Object.entries(example.observations).map(([id, input]) => ({
    $type: classes.FetchedFileObservation.alias, id, observedSHA256: input.observedSHA256,
  } satisfies FetchedFileObservation));
}

function notFoundObservation(input: typeof missingCase.notFound) {
  if (input.httpStatus !== 404 || "observedSHA256" in input || "body" in input) {
    throw new Error("PB-MISSING expects HTTP 404 without payload bytes or an observed digest");
  }
  return {
    $type: classes.PayloadNotFoundObservation.alias, id: "notFound", httpStatus: input.httpStatus,
  } satisfies PayloadNotFoundObservation;
}

type Observation = (FetchedFileObservation | PayloadNotFoundObservation) & { id: string };

function fileModel(
  example: ComparisonCase,
  target: (ManifestEntry | LocalMetadataFile) & { id: string },
  observations: Observation[] = fetchedObservations(example),
) {
  const { source } = example;
  const requirement = { $type: core.Requirement.alias, id: source.requirement } satisfies Requirement;
  const criterion = { $type: core.AcceptanceCriterion.alias, id: source.criterion } satisfies AcceptanceCriterion;
  const test = { $type: core.Test.alias, id: source.test } satisfies Test;

  return {
    nodes: [requirement, criterion, test, target, ...observations],
    edges: [
      { relation: trace.requirementValidatedByCriterion.alias, from: requirement.id, to: criterion.id },
      { relation: trace.testValidatesRequirement.alias, from: test.id, to: requirement.id },
      ...observations.flatMap(o => [
        {
          relation: o.$type === classes.FetchedFileObservation.alias
            ? relations.comparedAgainst.alias
            : relations.requestedEntry.alias,
          from: o.id,
          to: target.id,
        },
        { relation: trace.evidenceSupportsCriterion.alias, from: o.id, to: criterion.id },
      ]),
    ],
  };
}

const metadataPaths = new Map([
  ["PB-MANIFEST", "artifact_manifest.json"],
  ["PB-CHECKSUMS", "checksums.sha256"],
]);

function metadataModel(example: ComparisonCase & { localMetadataFile: Pick<LocalMetadataFile, "path" | "expectedSHA256"> }) {
  const file = example.localMetadataFile;
  const expectedPath = metadataPaths.get(example.source.criterion);
  if (file.path !== expectedPath) {
    throw new Error(`${example.source.criterion} expects ${expectedPath}, got ${file.path}`);
  }
  return fileModel(example, { $type: classes.LocalMetadataFile.alias, id: file.path, ...file });
}

function manifestEntry(entry: Pick<ManifestEntry, "path" | "expectedSHA256">) {
  return { $type: classes.ManifestEntry.alias, id: entry.path, ...entry } satisfies ManifestEntry;
}

export const models = {
  "PB-PAYLOAD": fileModel(payloadCase, manifestEntry(payloadCase.manifestEntry)),
  "PB-MANIFEST": metadataModel(manifestCase),
  "PB-CHECKSUMS": metadataModel(checksumsCase),
  "PB-MISSING": fileModel(missingCase, manifestEntry(missingCase.manifestEntry), [
    ...fetchedObservations(missingCase), notFoundObservation(missingCase.notFound),
  ]),
};
