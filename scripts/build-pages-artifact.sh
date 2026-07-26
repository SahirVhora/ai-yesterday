#!/usr/bin/env bash
set -euo pipefail

output="${1:-_site}"
case "$output" in
  _site)
    ;;
  *)
    echo "Refusing artifact path outside _site: $output" >&2
    exit 1
    ;;
esac

rm -rf "$output"
mkdir -p "$output/data"

cp index.html favicon.svg preview.png robots.txt sitemap.xml _headers .nojekyll "$output/"
cp data/digest.json "$output/data/"
cp -R data/history "$output/data/"

for forbidden in scripts docs tests linkedin-drafts .github README.md CONTRIBUTING.md SECURITY.md LICENSE; do
  if [ -e "$output/$forbidden" ]; then
    echo "Forbidden path in Pages artifact: $forbidden" >&2
    exit 1
  fi
done
