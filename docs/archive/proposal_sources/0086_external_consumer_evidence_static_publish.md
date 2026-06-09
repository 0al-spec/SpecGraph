# External Consumer Evidence Static Publish

## Draft Plan

Publish `runs/external_consumer_evidence_index.json` in the public static
artifact bundle so accepted downstream consumer evidence is HTTP-readable after
SpecGraph publish.

## Scope

- Add `external_consumer_evidence_index.json` to required public run surfaces.
- Refresh external consumer handoffs and evidence before bundle collection.
- Update static publish documentation and DocC mirror.
- Add static bundle regression coverage.
- Do not change evidence acceptance semantics.
- Do not mutate SpecSpace or Platform.
- Do not add a new evidence artifact family.

## Validation Intent

- focused static bundle tests
- `make publish-bundle PUBLISH_BUNDLE_FLAGS=`
- `make docc-sync`
- proposal tracking gates
- full Python suite
