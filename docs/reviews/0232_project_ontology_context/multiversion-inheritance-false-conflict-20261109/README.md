# False inheritance conflict with multiple core versions

On 2026-11-09, local integration tests found that the ONT-087 candidate at
Ontology PR #114 head `36599e244c05945691e6f8979984e0808db4a2f4` reported
`class.field.target.namespace_conflict` for valid staged models that imported
different versions of `specgraph-core`. Two existing tests in
[`tests/test_ontology_advice_release.py`](../../../../tests/test_ontology_advice_release.py)
failed when both `0.3.0` and `0.4.0` sources were supplied, including the
index-aware hook's multi-version test.

The candidate considered every supplied package as a possible runtime target,
even when a version was not reachable from the checked model's imports. The
fix restricts target-identity comparisons to the model's exact transitive
import closure; it still rejects competing reachable declarations. A later
local candidate passed all five existing advisory integration tests. See
[Ontology PR #114](https://github.com/0al-spec/Ontology/pull/114) for the
change and hosted review.

This observation records a defect found before that candidate was merged. It
does not claim the original 0.10.0 release emitted these new diagnostics or
that the fix has been released. Local test results do not prove deployed state.
