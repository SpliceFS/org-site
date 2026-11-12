# splicefs.org

The website of the SpliceFS project, https://splicefs.org: the home page and the
[comparison](https://splicefs.org/compare/) with other file systems.

The pages are plain HTML files in `site/`. There is no build step and no framework.

```
site/index.html            the home page
site/compare/index.html    how SpliceFS compares, and where it is headed
```

## Changing a page

Edit the file, look at it, and open a pull request:

```
python3 -m http.server --directory site 8000    # then open http://localhost:8000
make check                                       # the pages are well formed and their links lead somewhere
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
