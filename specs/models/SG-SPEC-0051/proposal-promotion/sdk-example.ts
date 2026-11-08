// Bounded in-memory illustration only; this is not the SpecGraph publication gate.
import { trigger, type ActionRelationship } from "./generated/relations";
import { ActionRelationshipRecordSchema } from "./generated/validators";
import { TransitionRecordSchema } from "./generated/schemas";
import type { MaterializeSpecDraft, PromoteProposalToSpecDraft, TransitionRecord } from "./generated/types";

function requireCondition(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}

function locator(value: unknown): string {
  requireCondition(typeof value === "string" && value.length > 0, "unsupported locator");
  return value;
}

function decision(id: string, edge: string, source: string, target: string): TransitionRecord {
  return {
    $type: "sgpromotion:TransitionRecord",
    transition_record_id: id,
    transition_identifier: `${id}:v1`,
    promotion_edge: edge,
    gate_type: "review",
    reviewer_or_decider: "fixture-reviewer",
    decision_timestamp: "2026-01-01T00:00:00Z",
    outcome: "approved",
    rationale: "Synthetic example only",
    source_ref: source,
    target_ref: target,
  };
}

const ingress = decision("ingress-1", "proposal -> spec_draft", "proposal-1", "draft-1");
const canonical = decision("canonical-1", "spec_draft -> canonical_artifact", "draft-1", "target-1");
const rejected = { ...ingress, transition_record_id: "rejected-1", outcome: "rejected" };
const foreign = decision("foreign-1", "proposal -> spec_draft", "proposal-2", "draft-2");
const records = new Map([ingress, canonical, rejected, foreign].map((record) => [record.transition_record_id, record]));

function requireRecord(id: string, edge: string, source: string, target: string): TransitionRecord {
  const record = records.get(id);
  requireCondition(record && TransitionRecordSchema.safeParse(record).success, "record not found");
  requireCondition(
    record.transition_record_id === id && record.transition_identifier.length > 0 &&
      record.reviewer_or_decider.length > 0 && record.decision_timestamp.length > 0 &&
      record.rationale.length > 0 && record.promotion_edge === edge &&
      record.source_ref === source && record.target_ref === target &&
      (record.gate_type === "review" && record.outcome === "approved" ||
        edge === "spec_draft -> canonical_artifact" && record.gate_type === "confirmation" && record.outcome === "confirmed"),
    "record does not authorize this example transition",
  );
  return record;
}

const drafts = new Map<string, string>();
const published = new Set<string>();
const proposal = { $type: "sgproposal:Proposal" as const, id: "proposal-1" };
const draft = { $type: "sgpromotion:SpecDraft" as const, id: "draft-1" };
const toDraft: PromoteProposalToSpecDraft = {
  $type: "sgpromotion:PromoteProposalToSpecDraft",
  targetDraft: { target: "sgpromotion:SpecDraft", locator: draft.id },
  transitionRecord: { target: "sgpromotion:TransitionRecord", locator: ingress.transition_record_id },
};
const toCanonical: MaterializeSpecDraft = {
  $type: "sgpromotion:MaterializeSpecDraft",
  target: { target: "sgpromotion:CanonicalTarget", locator: "target-1" },
  ingressRecord: { target: "sgpromotion:TransitionRecord", locator: ingress.transition_record_id },
  transitionRecord: { target: "sgpromotion:TransitionRecord", locator: canonical.transition_record_id },
};
const ingressActor = {
  $type: "sgpromotion:PromotionActor" as const,
  id: "fixture-promoter",
  run: (action: PromoteProposalToSpecDraft, source: typeof proposal) => {
    const target = locator(action.targetDraft.locator);
    const id = locator(action.transitionRecord.locator);
    requireRecord(id, "proposal -> spec_draft", source.id, target);
    drafts.set(target, id);
  },
};
const materializer = {
  $type: "sgpromotion:PromotionActor" as const,
  id: "fixture-materializer",
  run: (action: MaterializeSpecDraft, source: typeof draft) => {
    const ingressId = locator(action.ingressRecord.locator);
    const canonicalId = locator(action.transitionRecord.locator);
    const target = locator(action.target.locator);
    requireCondition(drafts.get(source.id) === ingressId && ingressId !== canonicalId, "foreign ingress");
    requireRecord(ingressId, "proposal -> spec_draft", proposal.id, source.id);
    requireRecord(canonicalId, "spec_draft -> canonical_artifact", source.id, target);
    published.add(target);
  },
};
const proposalAction: ActionRelationship<"sgpromotion:promotesProposalToDraft"> = {
  relation: "sgpromotion:promotesProposalToDraft", subject: ingressActor, action: toDraft, object: proposal,
};
const publishAction: ActionRelationship<"sgpromotion:materializesSpecDraft"> = {
  relation: "sgpromotion:materializesSpecDraft", subject: materializer, action: toCanonical, object: draft,
};

async function rejectsWithoutChange(action: () => void | Promise<void>): Promise<void> {
  const before = JSON.stringify([[...drafts], [...published]]);
  let rejectedAction = false;
  try { await action(); } catch { rejectedAction = true; }
  requireCondition(rejectedAction, "invalid transition unexpectedly succeeded");
  requireCondition(JSON.stringify([[...drafts], [...published]]) === before, "rejection changed state");
}

async function main(): Promise<void> {
  requireCondition(ActionRelationshipRecordSchema.safeParse(proposalAction).success, "valid shape rejected");
  requireCondition(TransitionRecordSchema.safeParse(rejected).success, "rejected decision is still a record");
  requireCondition(!ActionRelationshipRecordSchema.safeParse({
    ...proposalAction, action: { ...toDraft, targetDraft: { target: "sgpromotion:CanonicalTarget", locator: "target-1" } },
  }).success, "wrong reference target accepted");
  await rejectsWithoutChange(() => trigger(publishAction));
  await rejectsWithoutChange(() => trigger({ ...proposalAction, action: {
    ...toDraft, transitionRecord: { ...toDraft.transitionRecord, locator: "missing" },
  } }));
  await rejectsWithoutChange(() => trigger({ ...proposalAction, action: {
    ...toDraft, transitionRecord: { ...toDraft.transitionRecord, locator: rejected.transition_record_id },
  } }));
  await trigger(proposalAction);
  await rejectsWithoutChange(() => trigger({ ...publishAction, action: {
    ...toCanonical, ingressRecord: { ...toCanonical.ingressRecord, locator: foreign.transition_record_id },
  } }));
  await rejectsWithoutChange(() => trigger({ ...publishAction, action: {
    ...toCanonical, transitionRecord: { ...toCanonical.transitionRecord, locator: "missing" },
  } }));
  requireCondition(!published.has("target-1"), "published before canonical decision");
  await trigger(publishAction);
  requireCondition(published.has("target-1"), "example did not reach selected target");
  console.log("promotion SDK example: PASS");
}

main().catch((error: unknown) => { console.error(error); throw error; });
