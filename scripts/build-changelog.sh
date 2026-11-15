#!/bin/sh
# Builds site/changelog/index.html from the change log files of the server, the client and
# the packages repository, and from the release lists of the three, so the page always shows
# what those repositories say.
#
# With CHANGELOG_DIR set, server.md, client.md, packages.md, server.json, client.json and
# packages.json are taken from that folder (for work without a network). Otherwise the file of
# each main branch and the release list of each repository are downloaded.
#
# GitHub limits requests without a login. When GITHUB_TOKEN is set, it is sent with the
# release list request. It goes to curl through standard input, so it is neither on the
# command line, where any user of the machine could read it, nor in any output.
set -eu

cd "$(dirname "$0")/.."

# fetch_releases URL FILE
fetch_releases() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        printf 'Authorization: Bearer %s\n' "$GITHUB_TOKEN" |
            curl -fsS --retry 3 -H @- -o "$2" "$1"
    else
        curl -fsS --retry 3 -o "$2" "$1"
    fi
}

dir="${CHANGELOG_DIR:-}"
if [ -z "$dir" ]; then
    dir="$(mktemp -d)"
    trap 'rm -rf "$dir"' EXIT
    for part in server client packages; do
        curl -fsS --retry 3 -o "$dir/$part.md" \
            "https://raw.githubusercontent.com/SpliceFS/$part/main/CHANGELOG.md"
        fetch_releases "https://api.github.com/repos/SpliceFS/$part/releases?per_page=100" \
            "$dir/$part.json"
    done
fi

mkdir -p site/changelog
# Written under another name first: a build that fails must not leave half a page behind.
scripts/changelog.py "$dir/server.md" "$dir/client.md" "$dir/packages.md" \
    "$dir/server.json" "$dir/client.json" "$dir/packages.json" \
    > site/changelog/index.html.new
mv site/changelog/index.html.new site/changelog/index.html
echo "change log page: built"
