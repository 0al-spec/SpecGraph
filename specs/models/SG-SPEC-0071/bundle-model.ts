import example from "./all-case.json";
import { classes } from "./generated/payload/refs";
import { manifestEntry, notFoundObservation, publicationGraph } from "./publication-graph";
import type { FileCheck } from "./publication-graph";

const metadataPaths = ["artifact_manifest.json", "checksums.sha256"] as const;
type Reading = { url: string; observedSHA256: string } | { url: string; httpStatus: number };
interface BundleRun {
  remoteBaseURL: string;
  retained: Record<typeof metadataPaths[number], string>;
  observations: Reading[];
}

async function sha256(text: string) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
}

export async function assessBundle(run: BundleRun) {
  if (new URL(run.remoteBaseURL).protocol !== "https:") throw new Error("Expected an HTTPS origin");
  const base = run.remoteBaseURL.replace(/\/$/, "");
  const checks = new Map<string, FileCheck>();
  function expectFile(target: FileCheck["target"]) {
    const url = `${base}/${target.path}`;
    if (checks.has(url)) throw new Error(`Duplicate expected path: ${target.path}`);
    checks.set(url, { target: { ...target, id: `file:${target.path}` }, observations: [] });
  }
  for (const path of metadataPaths) {
    const body = run.retained[path];
    if (typeof body !== "string") throw new Error(`Missing retained metadata: ${path}`);
    expectFile({ $type: classes.LocalMetadataFile.alias, id: path, path, expectedSHA256: await sha256(body) });
  }
  const manifest = JSON.parse(run.retained["artifact_manifest.json"]);
  if (!Array.isArray(manifest.files)) throw new Error("Expected a manifest files array");
  for (const row of manifest.files) {
    if (typeof row.path !== "string" || !row.path || !isSHA256(row.sha256)) {
      throw new Error("Invalid manifest entry");
    }
    expectFile(manifestEntry({ path: row.path, expectedSHA256: row.sha256 }));
  }

  const failed = new Set<string>();
  for (const reading of run.observations) {
    const check = checks.get(reading.url);
    if (!check) throw new Error(`Unexpected request: ${reading.url}`);
    const { target, observations } = check;
    const id = `request:${observations.length}:${target.path}`;
    if ("httpStatus" in reading) {
      if (target.$type !== classes.ManifestEntry.alias) throw new Error("Expected a payload entry for HTTP 404");
      observations.push(notFoundObservation(id, reading));
      failed.add(target.path);
    } else {
      const { observedSHA256 } = reading;
      if (!isSHA256(observedSHA256)) throw new Error(`Invalid observed digest: ${target.path}`);
      observations.push({ $type: classes.FetchedFileObservation.alias, id, observedSHA256 });
      if (observedSHA256 !== target.expectedSHA256) failed.add(target.path);
    }
  }
  const files = [...checks.values()];
  const unchecked = files.filter(c => !c.observations.length).map(c => c.target.path);
  const status = failed.size ? "failed" : unchecked.length ? "incomplete" : "verified";
  return { ...publicationGraph(example.source, files), status, unchecked, failed: [...failed] };
}

function isSHA256(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}
