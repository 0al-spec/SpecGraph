# Source: mechanically checked specification authoring

Recorded from the current SpecGraph conversation on 2026-10-30. These excerpts
are attributed to the human participant by the capturing agent. The recording
date is not an authenticated utterance timestamp; identity and the original
chat transport are not independently attested. No private chat archive or
unrelated conversation is included.

## Human source excerpts

### Large leaf specifications

> Ну, я верю что может быть большая конечная спека, которую можно реализовать за один условно проход без уточнения дочерними спеками, но для уверенности надо уметь вычислять это более-менее надежно.

### Mechanical rather than model-only assessment

> Это всё некий семантический анализ
>
> А меня интересует нечто формально-механическое

### Existing ontology, metrics and graph

> Вот у меня есть метрики пакета SIB. Вот они, соответственно, тоже, хоть и про имплементацию, но там внутри них есть такие вещи, которые могут намекать на какие-то дефекты в спецификациях.

> В общем-то довольно много уже есть в самом SpecGraph, мы уже насочиняли больше 70 спецификаций, не просто так, а вот ориентируясь на существующие проверки и вычисления.

### Bounded authoring example

> Вот-вот. Видишь, мои пожелания не на пустом месте. Так что давай с учетом всего подумаем, на примере спеки про онтологию, как это формализовать в процессе написания спец.

### Agreement and durable graph memory

> Да. Всё верно. Зафиксируем в proposal? Или в каких-то заметках? А то забудем иначе. Всё должно оставаться на общем графе так или иначе. Он как система мысшления+память.

The final excerpt agrees with the preceding design direction and requests its
preservation. It does not grant a new canonical writer permission, activate a
runtime profile or approve every engineering detail below.

## Assistant synthesis accepted as a direction

During authoring, connect an explicit obligation to its ontology use, acceptance
case and verification method; run existing mechanical checks over a frozen
scope; retain concrete gaps separately from complexity signals; refine the
same node or propose delegation according to the existing bounded-concern
contract. A large, sufficiently specified leaf need not acquire child specs
because of its size. Ontology, native BDD, Supervisor diagnostics and SIB are
the starting point, not competing new authorities.

The proposed first example is SG-SPEC-0072's outcome precedence for ontology
context verification. Planned sensitivity probes remove a binding or required
case and introduce a conflicting result. These probes have not run. Compiler
validity, scenario declaration, verifiability, execution and approval remain
distinct observations.

## Engineering interpretation requiring review

- Use one scoped authoring profile to select applicable obligations and checks;
  do not require every relation of the ontology on every draft.
- Preserve obligation IDs and explicit partial/deferred mappings so deleting
  authoring content does not silently shrink the expected inventory.
- Treat unavailable tooling separately from a missing definition or binding.
- Keep SIB denominators, unknown inputs, source revisions and metric profiles
  visible; do not turn a proxy score into a completeness claim.
- Store this direction in the existing intent/proposal graph lanes, with a
  return task for Supervisor. No new canonical node kind is needed.

The implementation plan and its boundaries are in
[SG-RFC-0233](../../proposals/0233_mechanical_specification_authoring.md).
