#!/bin/sh
# Builds site/changelog/index.html from the change log files of the server, the client and
# the packages repository, so the page always shows what those repositories say.
#
# With CHANGELOG_DIR set, server.md, client.md and packages.md are taken from that folder
# (for work without a network). Otherwise the file of each main branch is downloaded.
set -eu

cd "$(dirname "$0")/.."

dir="${CHANGELOG_DIR:-}"
if [ -z "$dir" ]; then
    dir="$(mktemp -d)"
    trap 'rm -rf "$dir"' EXIT
    for part in server client packages; do
        curl -fsS --retry 3 -o "$dir/$part.md" \
            "https://raw.githubusercontent.com/SpliceFS/$part/main/CHANGELOG.md"
    done
fi

mkdir -p site/changelog
# Written under another name first: a build that fails must not leave half a page behind.
scripts/changelog.py "$dir/server.md" "$dir/client.md" "$dir/packages.md" \
    > site/changelog/index.html.new
mv site/changelog/index.html.new site/changelog/index.html
echo "change log page: built"
