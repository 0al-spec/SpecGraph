import { model } from "./model";
import { relationDefinitions as localRelations } from "./generated/pilot/relations";
import { relationDefinitions as coreRelations } from "./generated/sgcore/relations";
import { allRefs, relations as coreRefs } from "./generated/sgcore/refs";
import * as ontology from "./generated/pilot/ontology.normalized.json";

declare const process: { stdout: { write(value: string): void }; exitCode: number };
type Finding = { path: string; message: string };
const findings: Finding[] = [];
const fail = (path: string, message: string) => findings.push({ path, message });
const nodes = [model.specification, model.requirement, model.scenario, ...model.checks];
const ids = new Map(nodes.map(node => [node.id, node]));
// Inspect the instance graph even when deleting an edge narrows the author's literal union.
const edges: ReadonlyArray<{ relation: string; from: string; to: string }> = model.relations;
if (ids.size !== nodes.length) fail("model.ts", "Duplicate node identity");
for (const node of nodes) if (!node.id) fail("model.ts", "Missing node identity");
const definitions = [...localRelations, ...coreRelations];
const seen = new Set<string>();
for (const [index, edge] of edges.entries()) {
  const path = `model.ts/relations/${index}`;
  const identity = JSON.stringify(edge);
  if (seen.has(identity)) fail(path, "Duplicate relation instance");
  seen.add(identity);
  const definition = definitions.find(item => item.fqid === edge.relation);
  const source = ids.get(edge.from), target = ids.get(edge.to);
  if (!definition || !source || !target) fail(path, "Unresolved relation or endpoint");
  else if (source.$type !== definition.domain || target.$type !== definition.range)
    fail(path, "Endpoints disagree with generated relation domain/range");
}
for (const definition of localRelations) for (const node of nodes) {
  if (node.$type !== definition.domain) continue;
  const count = edges.filter(edge => edge.from === node.id && edge.relation === definition.fqid).length;
  if (count < definition.cardinality.min || count > definition.cardinality.max)
    fail(`model.ts/${node.id}/${definition.id}`, "Required relation cardinality is not satisfied");
}
if (!edges.some(edge => edge.relation === coreRefs.definesRequirement.alias
    && edge.from === model.specification.id && edge.to === model.requirement.id))
  fail("model.ts/relations", "This case requires its source Spec to define the selected Requirement");
function importedReferences(value: unknown): void {
  if (typeof value === "string" && /^sgcore:[A-Za-z][A-Za-z0-9_]*$/.test(value) && !(value in allRefs))
    fail("domain-ontology-package.yaml", `Imported symbol does not exist in compiled sgcore: ${value}`);
  else if (Array.isArray(value)) value.forEach(importedReferences);
  else if (value && typeof value === "object") Object.values(value).forEach(importedReferences);
}
importedReferences(ontology);
for (const [index, check] of model.checks.entries()) {
  if (!["verified", "unavailable", "invalid"].includes(check.outcome))
    fail(`model.ts/checks/${index}/outcome`, "Unsupported check outcome");
  if (!check.check.trim() || !check.detail.trim())
    fail(`model.ts/checks/${index}`, "Check identity and diagnostic must be nonempty");
}
if (!["verified", "unavailable", "invalid"].includes(model.scenario.expectedOutcome))
  fail("model.ts/scenario/expectedOutcome", "Unsupported expected outcome");
process.stdout.write(JSON.stringify({ model, findings }) + "\n");
process.exitCode = findings.length ? 1 : 0;
