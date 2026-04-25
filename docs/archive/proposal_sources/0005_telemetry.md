# SpecGraph Telemetry

Возьму за базу polyglot runtime + OTLP + OpenTelemetry Collector; если у вас k8s, VMs или agentified binaries под `zeroald/agentifyd`, меняется в основном только слой auto-instrumentation и exporters. В вашей экосистеме это особенно уместно: Agent Passport уже оставляет `Telemetry and Monitoring Integration` как открытый work item, а Hypercode TODO прямо просит `Configuration Inspector` и `Application Graph Visualizer` — то есть SpecGraph уже просится стать не просто spec-store, а evidence graph.  

## Чек-лист

* Сделать **OpenTelemetry canonical plane**, а **OpenTracing** оставить только как migration/shim layer.
* Ввести в SpecGraph каноническую цепочку: **Intent → SpecNode → Artifact → Runtime → Outcome → Adoption**.
* Развести роли сигналов: **traces** для пути, **metrics** для объёма/latency/adoption, **logs** для provenance и “почему так решил graph”.
* Описать свой `specgraph.*` semantic schema и генерировать из него SDK constants, Collector transforms и UI overlays.
* Для delayed adoption использовать не parent/child, а **span links** + durable correlation ledger.

## Roadmap

1. **Schema-first telemetry**: описать `specgraph.*` attributes/events/metrics в одном YAML-источнике и привязать их к node/edge типам. Проверка: schema lint + generated SDK wrappers. Успех: каждый `SpecNode` имеет telemetry contract. ([OpenTelemetry][1])
2. **Runtime propagation**: поднять OTel SDK/Collector, завести propagators, baggage и links, а legacy OpenTracing пустить через shim. Проверка: end-to-end trace continuity через HTTP/messaging/custom transports. Успех: >95% критичных intent-traces не рвутся. ([OpenTelemetry][2])
3. **Evidence plane**: Collector экспортирует не только в backend, но и в `SpecGraph Evidence Ingestor`, который апдейтит node/edge health и adoption overlays. Проверка: клик по node показывает traces/logs/metrics. Успех: graph visualizer живой, а не статический. 
4. **Adoption attribution**: immediate adoption остаётся в том же trace, delayed adoption заводит новый trace со span link на исходный intent/outcome. Проверка: из adoption metric можно провалиться в exemplar и выйти на связанный trace. Успех: видно time-to-value и retention по intent/spec/release. ([OpenTelemetry][3])

## TL;DR

Я бы **не пытался “встроить OpenTracing и OpenTelemetry одинаково”**. Для SpecGraph целевой архитектурой должен быть **OpenTelemetry everywhere**: traces + metrics + logs + resource attrs + baggage + links, передаваемые по **OTLP** через Collector. **OpenTracing** нужен только как временный мост для legacy-кода: сам проект OpenTracing архивирован и deprecated, а официальный migration path у OTel — поставить OTel SDK, подключить OpenTracing shim, писать весь новый instrumentation уже на OTel API и постепенно заменять старые вызовы. Более того, OTel compatibility layer сам предупреждает, что shim не стоит смешивать с baggage-dependent codepaths, а semantic convention mapping через shim специально почти не делается. ([GitHub][4])

---

## 1. Как я бы моделировал это в SpecGraph

Сделал бы в graph не только `SpecNode`, но и **observability edges**:

```text
Intent
  └─resolves_to─> SpecNode
      └─implemented_by─> Artifact
          └─deployed_as─> RuntimeEntity
              └─produces─> Outcome
                  └─attributed_to─> Adoption
```

Telemetry здесь — это не “ещё один лог сбоку”, а **evidence**, которое прикрепляется к node/edge. Это логично и для Hypercode-графа, и для 0AL, где процессы уже мыслятся как sandboxed/signed/introspectable сущности. 

Практически это означает:

* **Trace** отвечает: *какой путь прошёл конкретный intent?*
* **Metric** отвечает: *сколько таких intent-ов, с какой latency/error/adoption?*
* **Log/Event** отвечает: *почему graph resolver выбрал именно эти nodes/rules/policies?*
* **Graph DB** хранит агрегаты и связи как first-class state.

---

## 2. Что именно становится span, metric, log и resource

### Span’ы

Root domain span я бы заводил не на transport-уровне, а на уровне доменного намерения:

* `specgraph.intent.start`
* `specgraph.resolve`
* `specgraph.plan`
* `specgraph.execute`
* `specgraph.outcome.record`
* `specgraph.adoption.record` (для immediate adoption)

Transport spans (`HTTP`, `Messaging`, `DB`, `FaaS`, `GenAI`, `Feature Flags`) — это нижний слой, где нужно **reuse existing OTel semconv**, а не изобретать свои. OTel semantic conventions уже покрывают HTTP, messaging, feature flags, FaaS, GraphQL, GenAI и другие области. ([OpenTelemetry][1])

### Metrics

Метрики держал бы product-safe и low-cardinality:

* `specgraph.intent.requests`
* `specgraph.intent.errors`
* `specgraph.intent.duration`
* `specgraph.adoption.events`
* `specgraph.adoption.lag`
* `specgraph.specnode.coverage_ratio`

OTel прямо проектировался так, чтобы метрики коррелировались с trace-ами через **exemplars**, а их attributes могли обогащаться через **Baggage** и `Context`. ([OpenTelemetry][3])

### Logs / Events

Всё verbose и provenance-heavy — сюда:

* какие правила graph resolver matched
* какой selector победил
* какой policy override сработал
* почему node был skipped/denied/degraded

Это очень хорошо совпадает с вашим `Configuration Inspector`: он может строиться **не из span attributes**, а из коррелированных OTel logs. OTel logs специально сделаны так, чтобы работать с уже существующими логами, коррелироваться с другими сигналами и не дублировать traces. И OTel guidance прямо говорит: verbose data лучше держать в logs/events, а не распихивать по spans. ([OpenTelemetry][5]) 

### Resource и Instrumentation Scope

* `Resource` — кто производит telemetry: `service.name`, `deployment.environment.name`, `service.instance.id`, плюс ваши `specgraph.graph.id`, `specgraph.graph.version`. OTel resource conventions и custom resource attrs для этого как раз есть. ([OpenTelemetry][6])
* `Instrumentation scope` — какой логический модуль SpecGraph это эмитит: `specgraph.resolver`, `specgraph.executor`, `specgraph.adoption`, `specgraph.policy`. Это именно “logical unit within the application code”. ([OpenTelemetry][7])

### Baggage и Propagation

`Propagator`-ы в OTel предназначены для inject/extract traces и baggage через process boundaries. Baggage живёт рядом с context и может добавляться к traces, metrics и logs. ([OpenTelemetry][8])

Но в SpecGraph я бы разделил:

**metric-safe / baggage-safe**

* `specgraph.intent.class`
* `specgraph.spec.node_key`
* `specgraph.release.channel`
* `feature_flag.key`
* `feature_flag.variant`

**trace/log only (high cardinality)**

* `specgraph.intent.run_id`
* `specgraph.spec.node_id`
* `specgraph.artifact.digest`
* `agent.passport.uid`

Иначе вы убьёте cardinality в metrics.

---

## 3. Ключевое решение: свой `specgraph.*` semantic convention package

Это важный момент. Я бы не размазывал имена атрибутов по коду. Я бы завёл отдельный schema package, например:

```yaml
# specgraph.semconv.yaml  (упрощённо)
groups:
  - id: specgraph.intent
    type: span
    span_kind: internal
    brief: Domain intent execution in SpecGraph
    attributes:
      - id: specgraph.intent.name
        type: string
      - id: specgraph.intent.class
        type: string
      - id: specgraph.intent.run_id
        type: string

  - id: specgraph.spec
    type: attribute_group
    attributes:
      - id: specgraph.spec.node_id
        type: string
      - id: specgraph.spec.node_key
        type: string

  - id: specgraph.adoption
    type: metric
    metric_name: specgraph.adoption.events
```

Это не “самодеятельность”. OTel официально допускает и рекомендует для новых областей определять новые conventions в YAML и прототипировать их across signals, а не только для spans. ([OpenTelemetry][9])

Для вас это особенно ценно, потому что Hypercode уже мыслит себя schema-first/AOT-first системой. Поэтому pipeline мог бы быть таким:

```text
SpecGraph schema
  -> specgraph.semconv.yaml
  -> generated tracer/meter/logger constants
  -> Collector transforms
  -> dashboards
  -> Graph Visualizer overlays
```

---

## 4. Где здесь остаётся OpenTracing

Вот тут принцип жёсткий:

**OpenTracing = compatibility edge.
OpenTelemetry = canonical telemetry model.**

Официальный OTel migration path такой: поставить OTel SDK, заменить текущий OpenTracing tracer implementation, подключить OpenTracing shim, оставить старые вызовы жить, но весь новый instrumentation писать на OTel API и постепенно менять старые библиотеки на OTel equivalents. ([OpenTelemetry][2])

Но для SpecGraph есть два тонких риска:

1. **Shim не должен считаться вашим semantic layer.**
   OTel compatibility spec прямо говорит, что semantic convention mapping через OpenTracing shim **SHOULD NOT** выполняться, кроме error mapping. То есть старые OT tags/logs сами по себе не превратятся в `specgraph.*`. ([OpenTelemetry][10])

2. **Baggage через shim ненадёжен для важных flow.**
   Спецификация compatibility layer отдельно предупреждает: смешение shim и OTel API не рекомендуется, если OpenTracing-код потребляет baggage — propagation semantics могут ломаться. Для вас это критично, потому что именно baggage/context удобно использовать для `Intent → Adoption` корреляции. ([OpenTelemetry][10])

Отсюда правило:

* legacy сервисы могут временно жить на OpenTracing shim;
* но **SpecGraph context** (`specgraph.*`) должен устанавливаться в OTel boundary wrappers, а не надеяться на магию shim;
* весь новый доменный instrumentation — только OTel.

---

## 5. Как шить delayed adoption через traces

Вот здесь span links — лучший инструмент.

OTel span links нужны именно для случаев, когда операции **каузально связаны, но не живут в одном parent/child trace**; классический пример — queued or asynchronous follow-up work. ([OpenTelemetry][11])

Это идеально для adoption:

### Сценарий A: immediate adoption

Пользователь сделал intent, и value случилось в том же flow.
Тогда `specgraph.adoption.record` — обычный child span + metric exemplar.

### Сценарий B: delayed adoption

Intent был сегодня, adoption случился через 3 дня.
Тогда:

* в момент intent/outcome вы сохраняете `trace_id/span_id` или целый `traceparent` в domain event / attribution ledger;
* при later adoption начинаете **новый trace**;
* новый adoption span получает **link** на исходный outcome span;
* adoption metric эмитится с теми же low-cardinality attrs (`intent.class`, `spec.node_key`, `release.channel`).

Схематично:

```python
# intent side
with tracer.start_as_current_span("specgraph.outcome.record") as span:
    save_attribution(
        intent_run_id=intent.run_id,
        linked_span_context=span.get_span_context(),
        intent_class=intent.intent_class,
        spec_node_key=intent.spec_node_key,
    )

# days later, adoption side
saved = load_attribution(intent_run_id)
link = trace.Link(saved.linked_span_context)

with tracer.start_as_current_span("specgraph.adoption.record", links=[link]) as span:
    span.set_attribute("specgraph.adoption.stage", "retained_7d")
    adoption_events.add(
        1,
        {
            "specgraph.intent.class": saved.intent_class,
            "specgraph.spec.node_key": saved.spec_node_key,
            "specgraph.adoption.stage": "retained_7d",
        },
    )
```

---

## 6. Collector и evidence plane

OTLP у OTel stable для traces/metrics/logs, а Collector — vendor-agnostic узел для receive/process/export. Это и должен быть ваш “bus” между runtime и SpecGraph. ([OpenTelemetry][12])

Я бы делал так:

```yaml
# схематично
receivers:
  otlp:
    protocols:
      grpc: {}
      http: {}

processors:
  resourcedetection: {}
  transform/specgraph: {}   # normalize/redact/add attrs
  tail_sampling: {}         # keep errors + critical intents
  batch: {}

exporters:
  traces_backend: {}
  metrics_backend: {}
  logs_backend: {}
  specgraph_evidence: {}    # custom ingestor into graph DB

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [resourcedetection, transform/specgraph, tail_sampling, batch]
      exporters: [traces_backend, specgraph_evidence]
    metrics:
      receivers: [otlp]
      processors: [resourcedetection, transform/specgraph, batch]
      exporters: [metrics_backend, specgraph_evidence]
    logs:
      receivers: [otlp]
      processors: [resourcedetection, transform/specgraph, batch]
      exporters: [logs_backend, specgraph_evidence]
```

Sampling лучше делать гибридно: head sampling на горячем трафике + tail sampling в Collector для ошибок, критичных сервисов и важных intent-классов. У Collector есть соответствующие sampling processors, а official examples прямо показывают pattern “always keep critical services and all errors”. ([OpenTelemetry][13])

---

## 7. Что бы я показывал в UI SpecGraph

Сделал бы два режима.

### Graph Overlay

На каждом node/edge:

* request rate
* success/error ratio
* p50/p95
* latest release/artifact
* adoption conversion
* adoption lag

### Configuration / Decision Inspector

По клику на `SpecNode` или `Intent`:

* какие правила/селекторы matched
* какой override победил
* какие policy decisions были `allow/deny/shadow`
* какие traces/logs/metrics это подтверждают

Именно так `Application Graph Visualizer` и `Configuration Inspector` из Hypercode TODO превращаются из design docs в живую operational surface. 

---

## 8. Что добавить специально для 0AL / Agent Passport

Поскольку Agent Passport строится вокруг identity / integrity / policy enforcement и chain of trust, я бы добавил в spans/logs отдельный provenance слой:

* `agent.passport.uid`
* `agent.passport.issuer`
* `agent.policy.id`
* `agent.policy.decision`
* `agent.integrity.verified=true|false`

Только не тащил бы это в metric labels, если значения высоко-кардинальны. Это хорошо ложится на существующие требования паспорта про unique identification, security policies и cryptographic verification.  

---

## 9. Антипаттерны

Не делал бы так:

* **писать новый код на OpenTracing** — это уже legacy path; сам OpenTracing архивирован и deprecated. ([GitHub][4])
* **ожидать, что shim автоматически переведёт старые теги в `specgraph.*`** — spec прямо говорит обратное. ([OpenTelemetry][10])
* **класть `intent.run_id` и `spec.node_id` в metric labels** — получите cardinality explosion.
* **держать весь adoption analytics только в trace backend** — для cohort/retention всё равно нужен warehouse/product analytics слой; OTel здесь должен быть correlation fabric, а не единственное хранилище истины.
* **класть verbose resolver provenance в span attributes** — это лучше хранить в logs/events. ([OpenTelemetry][5])

---

## Мой итог

Если коротко, я бы встроил это так:

```text
SpecGraph = source of truth
OpenTelemetry = signal fabric
Collector = policy + routing plane
Graph Evidence Ingestor = joiner back into SpecGraph
OpenTracing = temporary ingress shim for legacy only
```

То есть не “observability рядом со SpecGraph”, а **SpecGraph, который сам порождает и поглощает telemetry как evidence**. Это особенно естественно для вашей линии Hypercode/0AL: декларативный graph, AOT/schema-first tooling, signed/policy-aware runtime и introspection by default.   

Назовите целевой стек — `Go`, `Rust`, `TypeScript`, `Java`, плюс backend (`Tempo/Jaeger`, `Prometheus`, `Loki`, `ClickHouse`) — и я переложу эту схему в конкретный `specgraph.semconv.yaml`, Collector config и runtime wrappers.

[1]: https://opentelemetry.io/docs/specs/semconv/ "OpenTelemetry semantic conventions 1.40.0 | OpenTelemetry"
[2]: https://opentelemetry.io/docs/compatibility/migration/opentracing/ "Migrating from OpenTracing | OpenTelemetry"
[3]: https://opentelemetry.io/docs/specs/otel/metrics/ "OpenTelemetry Metrics | OpenTelemetry"
[4]: https://github.com/opentracing/specification "GitHub - opentracing/specification: A place to document (and discuss) the OpenTracing specification.  This project is DEPRECATED! https://github.com/opentracing/specification/issues/163 · GitHub"
[5]: https://opentelemetry.io/docs/concepts/signals/logs/ "Logs | OpenTelemetry"
[6]: https://opentelemetry.io/docs/specs/semconv/resource/ "Resource semantic conventions | OpenTelemetry"
[7]: https://opentelemetry.io/docs/concepts/instrumentation-scope/ "Instrumentation scope | OpenTelemetry"
[8]: https://opentelemetry.io/docs/specs/otel/context/api-propagators/ "Propagators API | OpenTelemetry"
[9]: https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/ "How to write semantic conventions | OpenTelemetry"
[10]: https://opentelemetry.io/docs/specs/otel/compatibility/opentracing/ "OpenTracing Compatibility | OpenTelemetry"
[11]: https://opentelemetry.io/docs/concepts/signals/traces/ "Traces | OpenTelemetry"
[12]: https://opentelemetry.io/docs/specs/otlp/ "OTLP Specification 1.10.0 | OpenTelemetry"
[13]: https://opentelemetry.io/docs/concepts/sampling/ "Sampling | OpenTelemetry"
