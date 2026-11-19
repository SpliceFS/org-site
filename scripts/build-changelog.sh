#!/bin/sh
# Builds build/changelog/index.html from the change log files of the server, the client and
# the packages repository, and from the release lists of the three, so the page always shows
# what those repositories say. make build must have run first: it replaces the whole build folder.
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

# fetch_all_releases REPO FILE: every release of the repository, one page of 100 after
# another until a page comes back short, joined into one JSON list. A repository that tags
# every merge passes 100 releases soon, and a single page would drop the oldest silently.
fetch_all_releases() {
    page=1
    while :; do
        fetch_releases "https://api.github.com/repos/SpliceFS/$1/releases?per_page=100&page=$page" \
            "$2.page$page"
        count="$(python3 -c 'import json, sys; print(len(json.load(open(sys.argv[1]))))' "$2.page$page")"
        [ "$count" -lt 100 ] && break
        page=$((page + 1))
    done
    pages=""
    i=1
    while [ "$i" -le "$page" ]; do
        pages="$pages $2.page$i"
        i=$((i + 1))
    done
    # The file names come from mktemp and a counter: no spaces, so the split is safe.
    # shellcheck disable=SC2086
    python3 -c 'import json, sys; print(json.dumps([r for f in sys.argv[1:] for r in json.load(open(f))]))' \
        $pages > "$2"
}

dir="${CHANGELOG_DIR:-}"
if [ -z "$dir" ]; then
    dir="$(mktemp -d)"
    trap 'rm -rf "$dir"' EXIT
    for part in server client packages; do
        curl -fsS --retry 3 -o "$dir/$part.md" \
            "https://raw.githubusercontent.com/SpliceFS/$part/main/CHANGELOG.md"
        fetch_all_releases "$part" "$dir/$part.json"
    done
fi

mkdir -p build/changelog
# Written under another name first: a build that fails must not leave half a page behind.
scripts/changelog.py "$dir" > build/changelog/index.html.new
mv build/changelog/index.html.new build/changelog/index.html
echo "change log page: built"
