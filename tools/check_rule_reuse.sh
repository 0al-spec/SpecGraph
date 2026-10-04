#!/usr/bin/env bash
# Git/CLI adapter only: catalog authority and outcomes live in reviewed contracts.
set -euo pipefail
if [[ $# -ne 5 ]]; then
  echo 'usage: check_rule_reuse.sh ROOT ANALYZER BASE HEAD OUTPUT_DIRECTORY' >&2
  exit 2
fi
root=$1
analyzer=$2
base=$(git -C "$root" rev-parse --verify "${3}^{commit}")
head=$(git -C "$root" rev-parse --verify "${4}^{commit}")
output=$5
mkdir -p "$output"
catalog_path=tools/rule_reuse_catalog.toml
# A deleted head catalog must not turn the following PR into another bootstrap.
git -C "$root" show "${head}:${catalog_path}" > "$output/head-catalog.toml"

verify_report() {
  jq -e --arg base "$2" --arg head "$3" '
    .artifact_kind == "rule_reuse_report" and .schema_version == 1
    and .status == "complete" and .base_revision == $base and .head_revision == $head
  ' "$1" >/dev/null
}
# Validate the catalog that will become authoritative after this change lands.
# Comparing head to itself exercises schema, templates and canonical bindings
# without letting the proposed catalog weaken the current base comparison.
"$analyzer" check-rule-reuse "$root" \
  --catalog "$output/head-catalog.toml" --base "$head" --head "$head" \
  --output "$output/head-catalog-validation.json" --strict
verify_report "$output/head-catalog-validation.json" "$head" "$head"
strict=no
mode=bootstrap
base_catalog_entry=$(git -C "$root" ls-tree "$base" -- "$catalog_path")
if [[ -n "$base_catalog_entry" ]]; then
  git -C "$root" show "${base}:${catalog_path}" > "$output/catalog.toml"
  strict=yes
  mode=enforcing
else
  cp "$output/head-catalog.toml" "$output/catalog.toml"
  echo 'NOTICE: bootstrap catalog from head; exact findings are report-only until catalog lands.'
fi
printf '%s\n' "$mode" > "$output/mode.txt"
set -- check-rule-reuse "$root" \
  --catalog "$output/catalog.toml" --base "$base" --head "$head" \
  --output "$output/report.json" --store "$output/history.sqlite"
if [[ "$strict" == yes ]]; then set -- "$@" --strict; fi
"$analyzer" "$@"
# Bootstrap is not enforcement, but unavailable/invalid evidence still fails.
verify_report "$output/report.json" "$base" "$head"
jq --arg mode "$mode" -r '
  "## Registered rule reuse (" + $mode + ")",
  "Changed-file procedural copies: \(.before_reimplementations) → \(.after_reimplementations)",
  "New exact copies: \(.new_reimplementations)",
  "New near matches (review only): \(.new_near_matches)",
  "Static spec uses: \(.reused_specifications)",
  "Revisions: `\(.base_revision)` → `\(.head_revision)`"
' "$output/report.json" > "$output/summary.md"
