#!/usr/bin/env bash
# Require the exact PR head and a verified base-equivalent merge snapshot.
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
read -r -a parents <<< "$(git -C "$root" show -s --format=%P "$merge")"
if [[ ${#parents[@]} -ne 2 || ${parents[1]} != "$pr_head" ]]; then
  echo 'rule reuse merge snapshot does not match the supplied base and PR head' >&2
  exit 1
fi
merge_base=${parents[0]}
if [[ $merge_base != "$base" ]]; then
  # Native stacks use the lower PR's merge snapshot. Accept only a two-parent
  # virtual base whose second parent is exactly this base and whose complete
  # tree is identical to the base. Require the PR head to contain the base.
  read -r -a virtual_parents <<< "$(git -C "$root" show -s --format=%P "$merge_base")"
  if [[ ${#virtual_parents[@]} -ne 2 || ${virtual_parents[1]} != "$base" ]] \
    || [[ $(git -C "$root" rev-parse "${merge_base}^{tree}") != "$(git -C "$root" rev-parse "${base}^{tree}")" ]] \
    || ! git -C "$root" merge-base --is-ancestor "$base" "$pr_head"; then
    echo 'rule reuse virtual base is not equivalent to the supplied base and PR head' >&2
    exit 1
  fi
fi
mkdir -p "$output"
jq -n --arg base "$base" --arg pr_head "$pr_head" --arg merge "$merge" \
  '{base_revision:$base,pr_head_revision:$pr_head,merge_revision:$merge}' \
  > "$output/comparison.json"
bash "$(dirname "${BASH_SOURCE[0]}")/check_rule_reuse.sh" \
  "$root" "$analyzer" "$base" "$merge" "$output"
