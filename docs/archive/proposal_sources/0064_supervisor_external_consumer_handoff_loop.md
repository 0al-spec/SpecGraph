# Source Draft: Supervisor External Consumer Handoff Loop

Operator concern:

> В целом ок. Вообще, у меня вся работа - supervisor centric, он подбирает
> gaps из спек и закрывает их. Но тут меня смущает наличие SpecSpace - он не
> реализуется через supervisor из SpecGraph. Поэтому и возник такой вопрос.

Decision captured by the promoted proposal:

- keep SpecGraph supervisor as the canonical gap finder and contract producer;
- treat SpecSpace as an external implementation consumer, not as SpecGraph
  canonical authority;
- formalize handoff artifacts from SpecGraph to SpecSpace;
- require consumer evidence before SpecGraph marks consumer-facing gaps closed;
- keep Platform/deploy work downstream of stable producer/consumer contracts.

