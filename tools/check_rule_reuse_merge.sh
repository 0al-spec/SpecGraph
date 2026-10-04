#!/usr/bin/env bash
# Require the exact GitHub base + PR-head merge snapshot before analysis.
set -euo pipefail
if [[ $# -ne 6 ]]; then
  echo 'usage: check_rule_reuse_merge.sh ROOT ANALYZER BASE PR_HEAD MERGE OUTPUT_DIRECTORY' >&2
  exit 2
fi
root=$1
analyzer=$2
base=$(git -C "$root" rev-parse --verify "${3}^{commit}")
pr_head=$(git -C "$root" rev-parse --verify "${4}^{commit}")
merge=$(git -C "$root" rev-parse --verify "${5}^{commit}")
output=$6
if [[ $(git -C "$root" rev-parse "${merge}^1") != "$base" \
   || $(git -C "$root" rev-parse "${merge}^2") != "$pr_head" ]]; then
  echo 'rule reuse merge snapshot does not match the supplied base and PR head' >&2
  exit 1
fi
mkdir -p "$output"
jq -n --arg base "$base" --arg pr_head "$pr_head" --arg merge "$merge" \
  '{base_revision:$base,pr_head_revision:$pr_head,merge_revision:$merge}' \
  > "$output/comparison.json"
bash "$(dirname "${BASH_SOURCE[0]}")/check_rule_reuse.sh" \
  "$root" "$analyzer" "$base" "$merge" "$output"
