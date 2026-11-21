# splicefs.org

The website of the SpliceFS project, https://splicefs.org: the home page, how it works, the
[comparison](https://splicefs.org/compare/) with other file systems, the
[install page](https://splicefs.org/install/), and the change log.

The pages are plain HTML files in `site/`. There is no framework. Each page holds a marker line
where the parts every page shares go, and `make build` writes the finished pages into `build/`:

```
site/index.html                 the home page: what SpliceFS is and who it is for
site/how-it-works/index.html    one file from the servers to the reader, in pictures
site/compare/index.html         how SpliceFS compares, and where it is headed
site/install/index.html         the commands to install it, by system
scripts/changelog-page.html     the template of the change log page (built, not kept here)
parts/                          the shared parts: head, style-base, header, footer
build/                          the finished pages; this is what is checked and published
```

## The shared parts

The head lines, the style rules every page uses, the logo with the menu, and the footer are
written once, as the files in `parts/`. A page has a marker line where a part goes:

```
<!-- part: header current=/install/ -->
```

The line is replaced by `parts/header.html`. After the part name come values, written
`name=value` (in double quotes when the value holds spaces); the part holds the places for them as
`{{name}}`, or `{{name|default}}` when the value is optional. `current` is the path of the page
itself: the menu link to it gets `aria-current="page"`. Several lines are passed as a fill, written
before the marker line of the part:

```
<!-- fill: light-extra -->
  --one: 1;
<!-- end fill -->
<!-- part: style-base -->
```

A marker whose part file does not exist, a value the part does not use, or a fill that is never
closed stops the build with a message that names the page and the line. `scripts/pages.py` is the
builder (the text at its top is the full description), and the change log page is built with the
same parts. To change the menu or the footer, change the file in `parts/` and nothing else.

## The steps files

The uninstall commands and the commands of a person who runs the client as themselves are files of
the packages repository (`steps/*.sh`), because the tests of that repository run those very files.
The install page never holds their text. A code block holds a marker, and `make build` writes the
file in, escaped for HTML:

```
<pre><code><!-- steps: uninstall-apt --></code></pre>
```

`make steps` (run by `make build`) downloads the files the pages name into `.steps/`, from the
`main` branch of the packages repository, the same version the change log page is built from.
With `STEPS_DIR=folder` set, nothing is downloaded and that folder is read, by the build and by
the check. `make check` fails when a block of a built page does not read exactly its steps file.
`scripts/steps.py` has the details; `tests/fixtures/steps` holds the files the tests use.

## The change log page

`make changelog` builds it into `build/changelog/` (`scripts/changelog.py` with the page in
`scripts/changelog-page.html`) from the `CHANGELOG.md` and the GitHub release list of the server, the client and the packages
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
example. `make test` runs the tests of the builders, with no network.

## Changing a page

Edit the file, look at it, and open a pull request:

```
make changelog                                   # builds the pages and the change log page into build/
python3 -m http.server --directory build 8000    # then open http://localhost:8000
make check                                       # the pages are well formed and their links lead somewhere
```

When the change reaches `main`, the `Publish` workflow checks the pages, copies `build/` to the
server, and compares the live home page with the commit. The site is live about a minute after
the merge.

## What the pages must say

SpliceFS is alpha software. The pages state what it is today, with its gaps, and label plans as
plans. A comparison includes the rows where SpliceFS is weaker.

## How publishing works

The workflow pushes `build/` by rsync over ssh with a key that can read and write the folder of
this one website and do nothing else. The key is the repository secret `UPLOAD_SSH_KEY`; the
server's host key is the variable `UPLOAD_KNOWN_HOSTS`. `scripts/publish.sh` is the whole of it.
