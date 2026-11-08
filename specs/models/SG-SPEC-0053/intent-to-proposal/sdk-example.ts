// A bounded demonstration using the generated SDK, not the SpecGraph executor.
import { trigger, type ActionRelationship } from "./generated/relations";
import { ActionRelationshipRecordSchema } from "./generated/validators";
import type { InterpretFragmentForDraft, InterpretIntentForProposal } from "./generated/types";

const intent = { $type: "sgcore:Intent" as const, id: "intent-1" };
const action: InterpretIntentForProposal = {
  $type: "sgproposal:InterpretIntentForProposal",
  candidateProposal: { target: "sgcore:Proposal", locator: "candidate-1" },
};
const authorRecord = { $type: "sgproposal:ProposalAuthor" as const, id: "author-1" };
const record = {
  relation: "sgproposal:interpretsIntentForProposal" as const,
  subject: authorRecord,
  action,
  object: intent,
};

// A reference to an author must not be accepted as a reference to a proposal.
const wrongTarget: InterpretIntentForProposal = {
  $type: "sgproposal:InterpretIntentForProposal",
  // @ts-expect-error ProposalAuthor is a different reference target.
  candidateProposal: { target: "sgproposal:ProposalAuthor", locator: "author-1" },
};
void wrongTarget;

function requireCondition(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function main(): Promise<void> {
  requireCondition(ActionRelationshipRecordSchema.safeParse(record).success, "valid record rejected");
  requireCondition(
    !ActionRelationshipRecordSchema.safeParse({ ...record, action: { $type: action.$type } }).success,
    "missing candidate reference accepted",
  );
  requireCondition(
    !ActionRelationshipRecordSchema.safeParse({ ...record, action: wrongTarget }).success,
    "wrong candidate type accepted",
  );
  requireCondition(
    !ActionRelationshipRecordSchema.safeParse({ ...record, object: authorRecord }).success,
    "wrong relationship object accepted",
  );

  // These resolvers are examples, not claims about real authoring.
  const fragmentsByDraft = new Map<string, string[]>([["draft-1", []]]);
  const fragment = { $type: "sgcore:IntentFragment" as const, id: "fragment-1" };
  const draftAction: InterpretFragmentForDraft = {
    $type: "sgproposal:InterpretFragmentForDraft",
    candidateDraft: { target: "sgcore:IntentDraft", locator: "draft-1" },
  };
  const synthesizer = {
    $type: "sgproposal:IntentSynthesizer" as const,
    id: "synthesizer-1",
    run: (input: InterpretFragmentForDraft, selected: typeof fragment) => {
      const locator = input.candidateDraft.locator;
      if (typeof locator !== "string") throw new Error("unsupported draft locator");
      const links = fragmentsByDraft.get(locator);
      if (!links) throw new Error("draft not found");
      links.push(selected.id);
    },
  };
  const synthesis: ActionRelationship<"sgproposal:interpretsFragmentForDraft"> = {
    relation: "sgproposal:interpretsFragmentForDraft",
    subject: synthesizer,
    action: draftAction,
    object: fragment,
  };
  requireCondition(ActionRelationshipRecordSchema.safeParse(synthesis).success, "draft record rejected");
  requireCondition(
    !ActionRelationshipRecordSchema.safeParse({
      ...synthesis,
      action: { $type: draftAction.$type },
    }).success,
    "missing draft reference accepted",
  );
  requireCondition(fragmentsByDraft.get("draft-1")?.length === 0, "unexpected initial fragments");
  await trigger(synthesis);
  await trigger({ ...synthesis, object: { ...fragment, id: "fragment-2" } });
  requireCondition(
    fragmentsByDraft.get("draft-1")?.join() === "fragment-1,fragment-2",
    "fragments not recorded in the selected draft",
  );
  const draftBefore = JSON.stringify([...fragmentsByDraft]);
  let unknownDraftRejected = false;
  try {
    await trigger({
      ...synthesis,
      action: { ...draftAction, candidateDraft: { ...draftAction.candidateDraft, locator: "missing" } },
    });
  } catch {
    unknownDraftRejected = true;
  }
  requireCondition(unknownDraftRejected, "unknown draft accepted by the example resolver");
  requireCondition(JSON.stringify([...fragmentsByDraft]) === draftBefore, "unknown draft changed state");

  const candidateIntents = new Map<string, string[]>([["candidate-1", []]]);
  const author = {
    ...authorRecord,
    run: (input: InterpretIntentForProposal, selected: typeof intent) => {
      const locator = input.candidateProposal.locator;
      if (typeof locator !== "string") throw new Error("unsupported locator");
      const links = candidateIntents.get(locator);
      if (!links) throw new Error("candidate not found");
      links.push(selected.id);
    },
  };
  const executable: ActionRelationship<"sgproposal:interpretsIntentForProposal"> = {
    ...record,
    subject: author,
  };

  requireCondition(candidateIntents.get("candidate-1")?.length === 0, "unexpected initial link");
  await trigger(executable);
  requireCondition(candidateIntents.get("candidate-1")?.join() === intent.id, "link not recorded");

  const before = JSON.stringify([...candidateIntents]);
  let rejected = false;
  try {
    await trigger({
      ...executable,
      action: { ...action, candidateProposal: { ...action.candidateProposal, locator: "missing" } },
    });
  } catch {
    rejected = true;
  }
  requireCondition(rejected, "unknown candidate accepted by the example resolver");
  requireCondition(JSON.stringify([...candidateIntents]) === before, "unknown candidate changed state");
  console.log("intent-proposal SDK example: PASS");
}

main().catch((error: unknown) => {
  console.error(error);
  throw error;
});
