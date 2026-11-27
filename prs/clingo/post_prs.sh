#!/bin/bash
# Push pr/<name> branches to msoos/clingo and open one PR per NN-<name>.md against potassco/clingo:wip. Usage: [DRY_RUN=1] ./post_prs.sh
set -euo pipefail

DIR="$(dirname "$(realpath "$0")")"
CLINGO="$DIR/../../.."
run() { if [ -n "${DRY_RUN:-}" ]; then echo "+ $*"; else "$@"; fi; }

cd "$CLINGO"
for md in "$DIR"/[0-9][0-9]-*.md; do
  name=$(basename "$md" .md); name=${name#*-}
  branch="pr/$name"
  git rev-parse --verify -q "$branch" > /dev/null || { echo "missing branch $branch"; exit 1; }
  title=$(head -1 "$md" | sed 's/^# //')
  body=$(mktemp)
  tail -n +3 "$md" > "$body"
  run git push msoos "$branch"
  run gh pr create --repo potassco/clingo --base wip --head "msoos:$branch" --title "$title" --body-file "$body"
  rm -f "$body"
done
