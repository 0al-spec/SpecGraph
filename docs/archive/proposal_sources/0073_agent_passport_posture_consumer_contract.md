# Source Draft: Agent Passport Posture Consumer Contract

Operator plan:

> сделать синхронизированное изменение в SpecGraph и SpecSpace, где SpecGraph
> остаётся producer of truth, а SpecSpace отображает Agent Passport
> verification/enforcement posture.

Implementation constraints captured by the promoted proposal:

- start from merged `0072 Agent Passport Runtime Enforcement Posture`;
- keep SpecGraph as producer and SpecSpace as external consumer;
- extend the existing `external_consumer_handoff_packets` contract rather than
  creating a new handoff family;
- include `known_agent_passport_index` and
  `agent_passport_verification_report` in the SpecSpace artifact contract;
- declare display states and fallback states before implementing SpecSpace UI;
- do not claim runtime enforcement or implement SpecSpace UI in this slice.

