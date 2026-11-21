#!/bin/sh
# Downloads the steps files of the packages repository that the pages show in their code blocks
# (steps/*.sh) into .steps/, so that make build can fill the blocks from them. Only the files
# the pages name with a steps marker are fetched; scripts/steps.py lists them.
#
# The files are those of the main branch of the packages repository, the same version the
# change log page is built from. The Publish workflow runs again after each release of the
# packages, so the live page follows main.
#
# With STEPS_DIR set, nothing is downloaded: the build and the check read that folder (for
# work without a network, and for the tests).
set -eu

cd "$(dirname "$0")/.."

if [ -n "${STEPS_DIR:-}" ]; then
    echo "steps files: taken from $STEPS_DIR"
    exit 0
fi

# Names are checked by steps.py: letters, digits and hyphens, so they are safe in a URL.
names="$(python3 scripts/steps.py names site)"
# Written under another name first: a download that fails must not leave half a folder behind.
rm -rf .steps.new
mkdir .steps.new
trap 'rm -rf .steps.new' EXIT
count=0
for name in $names; do
    count=$((count + 1))
    curl -fsS --retry 3 -o ".steps.new/$name.sh" \
        "https://raw.githubusercontent.com/SpliceFS/packages/main/steps/$name.sh"
done
rm -rf .steps
mv .steps.new .steps
echo "steps files: downloaded $count from the packages repository"
