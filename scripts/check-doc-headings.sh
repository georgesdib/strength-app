#!/usr/bin/env bash
# Lists section headings that exist in HEAD but are missing from the working tree.
# A shared plan or contract rewritten from an older base silently drops sections added on
# another branch; this catches that before the commit. Deliberate removals: ALLOW_HEADING_REMOVAL=1.
set -euo pipefail

files=$(git diff --name-only HEAD -- '*.md' || true)
if [ -z "$files" ]; then
  echo "no markdown changes"
  exit 0
fi

status=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || continue
  old=$(git show "HEAD:$f" 2>/dev/null | grep -E '^#{2,3} ' || true)
  new=$(grep -E '^#{2,3} ' "$f" || true)
  removed=$(comm -23 <(printf '%s\n' "$old" | sort -u) <(printf '%s\n' "$new" | sort -u))
  if [ -n "$removed" ]; then
    echo "Headings removed from $f:"
    printf '%s\n' "$removed" | sed 's/^/  /'
    status=1
  fi
done <<< "$files"

if [ "$status" -ne 0 ]; then
  echo
  echo "Check each removal: a rename is fine, a silently dropped section is not."
  echo "Deliberate removal: ALLOW_HEADING_REMOVAL=1 $0"
fi
exit "$status"
