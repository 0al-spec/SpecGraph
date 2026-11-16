# GitView pilot observations for native YAML lint

GitView revised a canonical node and tried to check it in its original
workspace. SpecGraph runtime `3593bd75` rejected
`next-move --candidate-file specs/nodes/GITVIEW-SPEC-0003.yaml` with exit 1.
The candidate command intentionally accepts drafts under `docs/drafts/`.
The agent copied the canonical file to a temporary location under that directory.

The GitView pilot also recorded six successful draft identity checks and five
missing `updated_at` fields reported by the separately invoked YAML linter.
The identity result and the lint result cover different properties of the file.

The SpecGraph follow-up ran the packaged linter directly on
`specs/nodes/GITVIEW-SPEC-0003.yaml` and verified its SHA-256 was unchanged.
All 24 explicitly selected canonical GitView nodes passed the same linter.

Local 0AL sources and SHA-256 values

| Record | SHA-256 |
| --- | --- |
| `gitview/20261116T051800Z-note-canonical-candidate-check-friction.md` | `e6946d2af4b6df837751928233159ddbe315a6299171bcb2a3b8de7d5f5ad0e0` |
| `gitview/20261116T054800Z-note-candidate-check-lint-gap.md` | `ee71fc7024c174289556d7cd43028219d5e4bfc839bc29c062a983bccf879c16` |
| `specgraph/20261116T065116Z-status-gitview-canonical-yaml-lint-works-in-place.md` | `47b1b006e14ea4d2cf1e2fdd00e5282d1e4c62a865d5151424be7c29afefb7b6` |

The operator requested a separate native runtime lint command whose output
enumerates the checks performed.
