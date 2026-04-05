# Node Format Reference

> Canonical schema for SpecGraph nodes.
> Governed by [SG-SPEC-0001](../../specs/nodes/SG-SPEC-0001.yaml).
> Bootstrap schema for the current SpecGraph seed; child specs refine this
> contract before the graph is frozen.

## Envelope

Every node file uses the same top-level envelope regardless of kind.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: <ulid or uuidv7>             # immutable machine id
  key: <kind>.<dotted.human.path>   # stable human-readable key
  type: <node kind>                 # one of the registered kinds
  title: <string>                   # short human-readable name
  status: <lifecycle status>        # idea | stub | outlined | specified | linked | reviewed | frozen
  createdAt: <iso8601>
  updatedAt: <iso8601>
  revision: <integer>               # monotonically increasing
spec:
  # kind-specific payload (see below)
provenance:
  sources: []                       # list of {doc, section} references
  authoredBy: <string>              # person or agent who created this
  authority: <authority_class>      # authored | imported | inferred | distilled
lifecycle:
  supersededBy: <key | null>
  validFrom: <iso8601>
  validUntil: <iso8601 | null>
```

### Required fields (all kinds)

| Field | Type | Description |
|-------|------|-------------|
| `metadata.id` | string | Immutable machine identifier (ULID or UUIDv7) |
| `metadata.key` | string | Stable human-readable key (e.g., `feat.ui.button.hover`) |
| `metadata.type` | enum | Node kind |
| `metadata.title` | string | Short descriptive title |
| `metadata.status` | enum | Lifecycle status |
| `metadata.createdAt` | iso8601 | Creation timestamp |
| `metadata.updatedAt` | iso8601 | Last modification timestamp |
| `metadata.revision` | integer | Revision counter |
| `provenance.authority` | enum | Authority class |

### Optional fields (all kinds)

| Field | Type | Description |
|-------|------|-------------|
| `metadata.maturity` | float | Diagnostic signal 0.0-1.0 |
| `metadata.tags` | list[string] | Freeform classification tags |
| `provenance.sources` | list[object] | Source documents and sections |
| `provenance.authoredBy` | string | Creator identity |
| `lifecycle.supersededBy` | string/null | Key of superseding node |
| `lifecycle.validFrom` | iso8601 | Start of validity window |
| `lifecycle.validUntil` | iso8601/null | End of validity window |

---

## Schema Evolution

This document is the bootstrap contract for the current graph seed, not a
closed ontology. Root specs establish the stable core; child specs may refine
or extend the contract through explicit `refines` links while preserving
stable IDs and provenance.

---

## Kind: intent

Human-originated goal or product objective.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6A...
  key: intent.checkout.reduce-dropoff
  type: intent
  title: Reduce checkout abandonment
  status: outlined
  createdAt: 2026-03-16T10:00:00Z
  updatedAt: 2026-03-16T10:00:00Z
  revision: 1
spec:
  description: >
    Users abandon checkout at an unacceptable rate.  Reduce dropoff by
    improving load time and simplifying the payment step.
  intentKind: product            # product | technical | business | reliability | safety | compliance | ux | performance
  owner: egor
  priority: p1
provenance:
  sources:
    - doc: docs/authored/prd/checkout-v3.md
      section: "#goals"
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-03-16T10:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `description` | no | string | Detailed intent statement |
| `intentKind` | no | enum | Classification of intent |
| `owner` | no | string | Responsible person or team |
| `priority` | no | string | Priority level |

---

## Kind: spec

Structured artifact refining one or more intents into verifiable declarations.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6B...
  key: spec.checkout.v3
  type: spec
  title: Checkout v3
  status: specified
  createdAt: 2026-03-16T10:00:00Z
  updatedAt: 2026-03-17T14:00:00Z
  revision: 3
  maturity: 0.6
spec:
  objective: >
    Redesign the checkout flow to reduce abandonment by 30%.
  scope:
    in:
      - "Payment step simplification"
      - "Load time optimization"
    out:
      - "Account creation flow"
      - "Post-purchase experience"
  intentRefs:
    - intent.checkout.reduce-dropoff
  refines:
    - spec.checkout.root
  acceptance:
    - "First interactive action available within 1000 ms"
    - "Payment step requires at most 2 taps"
  acceptance_evidence:
    - criterion: "First interactive action available within 1000 ms"
      evidence: "criterion.checkout.first-interaction-fast defines success/failure signals"
    - criterion: "Payment step requires at most 2 taps"
      evidence: "criterion.checkout.payment-tap-count with threshold <= 2"
  terminology:
    dropoff: "User leaves checkout without completing payment."
  decisions:
    - id: D1
      statement: "Use streaming SSR for initial checkout render."
      rationale: "Reduces time-to-interactive below 1000 ms target."
  constraintRefs:
    - constraint.platform.ios-min-version
  dependsOn:
    - spec.payment.gateway-v2
provenance:
  sources:
    - doc: docs/authored/prd/checkout-v3.md
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-03-16T10:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `objective` | yes | string | What this spec achieves |
| `acceptance` | yes | list[string] | Acceptance criteria |
| `scope.in` | no | list[string] | What is in scope |
| `scope.out` | no | list[string] | What is out of scope |
| `intentRefs` | no | list[string] | Keys of parent intents |
| `refines` | no | list[string] | Keys of parent specs refined by this spec |
| `acceptance_evidence` | no | list[object] | 1:1 evidence for each criterion |
| `terminology` | no | map | Domain terms used in this spec |
| `decisions` | no | list[object] | Decisions with id, statement, rationale |
| `constraintRefs` | no | list[string] | Keys of applicable constraints |
| `dependsOn` | no | list[string] | Keys of dependency specs |
| `prompt` | no | string | Instruction for agent refinement |
| `outputs` | no | list[string] | Expected output file paths |
| `allowedPaths` | no | list[string] | Paths the agent may edit |

---

## Kind: requirement

A single verifiable demand derived from a spec or intent.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6C...
  key: req.checkout.first-interaction-fast
  type: requirement
  title: First checkout interaction under 1000 ms
  status: specified
  createdAt: 2026-03-16T10:00:00Z
  updatedAt: 2026-03-16T10:00:00Z
  revision: 1
spec:
  statement: >
    First interactive checkout action shall become available within 1000 ms
    of navigation start on target devices.
  sourceRef: spec.checkout.v3
  priority: p1
  verificationMode: runtime_verifiable   # manual | test_only | runtime_verifiable | mixed
  successSignals:
    - signal: "metric://ui.checkout.first_interaction_ms"
      operator: lte
      threshold: 1000
  failureSignals:
    - signal: "metric://ui.checkout.first_interaction_ms"
      operator: gt
      threshold: 1500
    - signal: "crash://checkout/session_abort"
      operator: exists
provenance:
  sources:
    - doc: docs/authored/specs/checkout-v3.md
      section: "#performance"
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-03-16T10:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `statement` | yes | string | The verifiable demand |
| `sourceRef` | yes | string | Key of originating spec or intent |
| `priority` | no | string | Priority level |
| `verificationMode` | no | enum | How this requirement is verified |
| `successSignals` | no | list[SignalCondition] | Conditions that indicate success |
| `failureSignals` | no | list[SignalCondition] | Conditions that indicate failure |

### SignalCondition

```yaml
signal: <string>          # signal URI (metric://, crash://, log://, etc.)
operator: <enum>          # eq | ne | gt | gte | lt | lte | exists | missing
threshold: <any>          # comparison value (omit for exists/missing)
```

---

## Kind: decision

An architectural or product decision with rationale (ADR).

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6D...
  key: adr.tooltip-delay-standardization
  type: decision
  title: Standardize tooltip delay at 300 ms
  status: reviewed
  createdAt: 2026-02-20T09:00:00Z
  updatedAt: 2026-02-20T09:00:00Z
  revision: 1
spec:
  statement: "All hover tooltips shall use a 300 ms delay before appearing."
  rationale: "Prevents accidental hover activation while remaining responsive."
  alternativesConsidered:
    - option: "100 ms delay"
      rejected: "Too sensitive — triggers on accidental mouse traversal."
    - option: "500 ms delay"
      rejected: "Feels sluggish in user testing."
provenance:
  sources:
    - doc: docs/authored/adr/tooltip-delay.md
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-02-20T09:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `statement` | yes | string | The decision |
| `rationale` | yes | string | Why this decision was made |
| `alternativesConsidered` | no | list[object] | Options that were rejected |

---

## Kind: constraint

A system-level limitation that bounds the solution space.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6E...
  key: constraint.platform.ios-min-version
  type: constraint
  title: Minimum iOS version is 16.0
  status: specified
  createdAt: 2026-01-10T08:00:00Z
  updatedAt: 2026-01-10T08:00:00Z
  revision: 1
spec:
  statement: "The application shall support iOS 16.0 and later."
  sourceRef: intent.platform.broad-reach
  enforcement: ci    # ci | runtime | manual | policy
provenance:
  sources:
    - doc: docs/authored/constraints/platform.md
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-01-10T08:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `statement` | yes | string | The constraint |
| `sourceRef` | no | string | Key of originating intent or spec |
| `enforcement` | no | enum | How the constraint is enforced |

---

## Kind: invariant

A stable property that must hold across all changes.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6F...
  key: inv.engine.no-crash-on-divzero
  type: invariant
  title: Division by zero must not crash
  status: reviewed
  createdAt: 2026-03-01T10:00:00Z
  updatedAt: 2026-03-01T10:00:00Z
  revision: 1
spec:
  statement: >
    Division by zero shall not crash the application.  The engine shall
    present an error state and allow recovery.
  scope: Engine
  verificationMode: test_only
provenance:
  sources:
    - doc: docs/authored/specs/calculator-mvp.md
      section: "#error-handling"
  authoredBy: egor
  authority: authored
lifecycle:
  supersededBy: null
  validFrom: 2026-03-01T10:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `statement` | yes | string | The invariant property |
| `scope` | no | string | Subsystem or module this applies to |
| `verificationMode` | no | enum | How the invariant is checked |

---

## Kind: code_surface

A stable implementation anchor identified by key, not file path.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6G...
  key: code.ui.button.tooltip-engine
  type: code_surface
  title: TooltipEngine component
  status: linked
  createdAt: 2026-03-17T11:00:00Z
  updatedAt: 2026-03-17T11:00:00Z
  revision: 1
spec:
  surfaceType: module      # symbol | module | screen | endpoint | workflow_step | job | worker | feature_branch
  taskRefs:
    - task.ui.tooltip-implementation
  criterionRefs:
    - req.checkout.first-interaction-fast
  runtimeSurfaceRefs:
    - runtime.ui.checkout-screen
  pathHint: src/components/tooltip/engine.ts   # informational only, NOT the stable identifier
provenance:
  sources: []
  authoredBy: codex-agent
  authority: inferred
lifecycle:
  supersededBy: null
  validFrom: 2026-03-17T11:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `surfaceType` | yes | enum | Kind of code anchor |
| `taskRefs` | no | list[string] | Keys of originating tasks |
| `criterionRefs` | no | list[string] | Requirements this implements |
| `runtimeSurfaceRefs` | no | list[string] | Runtime surfaces this maps to |
| `pathHint` | no | string | Informational file path (not authoritative) |

---

## Kind: test

A verification artifact covering requirements or acceptance criteria.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6H...
  key: test.ui.tooltip-delay
  type: test
  title: Tooltip delay test
  status: linked
  createdAt: 2026-03-17T12:00:00Z
  updatedAt: 2026-03-17T12:00:00Z
  revision: 1
spec:
  testType: integration     # unit | integration | e2e | manual | property
  covers:
    - req.checkout.first-interaction-fast
    - inv.engine.no-crash-on-divzero
  pathHint: tests/ui/test_tooltip_delay.py
provenance:
  sources: []
  authoredBy: codex-agent
  authority: inferred
lifecycle:
  supersededBy: null
  validFrom: 2026-03-17T12:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `covers` | yes | list[string] | Keys of requirements/invariants this test verifies |
| `testType` | no | enum | Classification of the test |
| `pathHint` | no | string | Informational file path |

---

## Kind: release

A versioned deployment artifact.

```yaml
apiVersion: specgraph.io/v0alpha1
kind: Node
metadata:
  id: node_01HQW6I...
  key: release.ios.2026.03.20.1
  type: release
  title: iOS 2026.03.20.1
  status: frozen
  createdAt: 2026-03-20T08:00:00Z
  updatedAt: 2026-03-20T08:00:00Z
  revision: 1
spec:
  versionTag: "2026.03.20.1"
  codeSurfaceRefs:
    - code.ui.button.tooltip-engine
    - code.checkout.payment-step
  rolloutScope:
    environment: prod
    channel: canary
    cohortPercent: 5
provenance:
  sources: []
  authoredBy: ci-pipeline
  authority: imported
lifecycle:
  supersededBy: null
  validFrom: 2026-03-20T08:00:00Z
  validUntil: null
```

### spec fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `versionTag` | yes | string | Release version identifier |
| `codeSurfaceRefs` | no | list[string] | Code surfaces included in this release |
| `rolloutScope` | no | object | Deployment scope (environment, channel, cohort) |

---

## Intent-atom format

For specs that use the atomic decomposition pattern (intents + premises):

```yaml
spec:
  atoms:
    intents:
      - id: "A-CALC-001"
        type: behavior         # requirement | invariant | behavior | constraint
        scope: Engine
        statement: "The calculator shall compute results for +, -, x, / on decimal numbers."
        premises: ["P-PROD-001"]
        verifiable_by: ["T-CALC-001"]
    premises:
      - id: "P-PROD-001"
        type: goal             # goal | assumption | constraint
        scope: Product
        statement: "Provide a minimal, reliable calculator feature set for MVP."
        evidence: "TBD"
```

This pattern is optional and complementary to the standard `acceptance` list.
It provides finer traceability when specs contain many independent assertions.
