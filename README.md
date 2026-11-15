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
repository. A row is one version of the code; a packaging change is shown in the row of the code
version that was current when it went out, and the packages version numbers are not shown. To
build it from local files: `CHANGELOG_DIR=folder make changelog`, with `server.md`, `client.md`,
`packages.md`, `server.json`, `client.json` and `packages.json` (the answers of
`GET /repos/SpliceFS/<repo>/releases?per_page=100`) in that folder.

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
