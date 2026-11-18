# splicefs.org

The website of the SpliceFS project, https://splicefs.org: the home page, how it works, the
[comparison](https://splicefs.org/compare/) with other file systems, and the change log.

The pages are plain HTML files in `site/`. There is no framework, and one page is built:

```
site/index.html                 the home page: what SpliceFS is and who it is for
site/how-it-works/index.html    one file from the servers to the reader, in pictures
site/compare/index.html         how SpliceFS compares, and where it is headed
site/changelog/index.html       built, not kept here: what each version changed
```

## The change log page

`make changelog` builds it (`scripts/changelog.py` with the page in `scripts/changelog-page.html`)
from the `CHANGELOG.md` and the GitHub release list of the server, the client and the packages
repository. A row is one version of the code. The packages column has two sources: the old
versions of the packages `CHANGELOG.md`, and the packages releases whose tag is a plain number
(1, 2, 3 ...), taken from the notes of each release. From a release's notes only the change
lines are used; the lines `Release of <program> <tag>.` and the `cut` comment are dropped, and
a release with no change line left adds nothing. A packaging change is shown in the row of the
newest server or client version published at or before it, newest change first in a row, and
the packages version numbers are not shown. To build the page from local files:
`CHANGELOG_DIR=folder make changelog`, with `server.md`, `client.md`, `packages.md`,
`server.json`, `client.json` and `packages.json` (the answers of
`GET /repos/SpliceFS/<repo>/releases?per_page=100`) in that folder; `tests/fixtures` is an
example. `make test` runs the tests of the builder, with no network.

## Changing a page

Edit the file, look at it, and open a pull request:

```
python3 -m http.server --directory site 8000    # then open http://localhost:8000
make check                                       # builds the change log page; the pages are well formed and their links lead somewhere
```

When the change reaches `main`, the `Publish` workflow checks the pages, copies `site/` to the
server, and compares the live home page with the commit. The site is live about a minute after
the merge.

## What the pages must say

SpliceFS is alpha software. The pages state what it is today, with its gaps, and label plans as
plans. A comparison includes the rows where SpliceFS is weaker.

## How publishing works

The workflow pushes `site/` by rsync over ssh with a key that can read and write the folder of
this one website and do nothing else. The key is the repository secret `UPLOAD_SSH_KEY`; the
server's host key is the variable `UPLOAD_KNOWN_HOSTS`. `scripts/publish.sh` is the whole of it.
