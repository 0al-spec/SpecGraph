import payloadCase from "./case.json";
import manifestCase from "./manifest-case.json";
import checksumsCase from "./checksums-case.json";
import missingCase from "./missing-case.json";
import { classes } from "./generated/payload/refs";
import type { FetchedFileObservation, LocalMetadataFile } from "./generated/payload/types";
import { manifestEntry, notFoundObservation, publicationGraph } from "./publication-graph";
import type { FileCheck, Observation } from "./publication-graph";

export { assessBundle } from "./bundle-model";

interface ComparisonCase {
  source: typeof payloadCase.source;
  observations: Readonly<Record<string, { observedSHA256: string }>>;
}

function fetchedObservations(example: ComparisonCase) {
  return Object.entries(example.observations).map(([id, input]) => ({
    $type: classes.FetchedFileObservation.alias, id, observedSHA256: input.observedSHA256,
  } satisfies FetchedFileObservation));
}

function fileModel(
  example: ComparisonCase,
  target: FileCheck["target"],
  observations: Observation[] = fetchedObservations(example),
) {
  return publicationGraph(example.source, [{ target, observations }]);
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

export const models = {
  "PB-PAYLOAD": fileModel(payloadCase, manifestEntry(payloadCase.manifestEntry)),
  "PB-MANIFEST": metadataModel(manifestCase),
  "PB-CHECKSUMS": metadataModel(checksumsCase),
  "PB-MISSING": fileModel(missingCase, manifestEntry(missingCase.manifestEntry), [
    ...fetchedObservations(missingCase), notFoundObservation("notFound", missingCase.notFound),
  ]),
};
