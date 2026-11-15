#!/usr/bin/env python3
"""Checks the pages before they are published.

Every HTML file must be plain ASCII, have balanced tags, and link only to pages that exist.
A page that fails here would be published broken, so the publish job runs this first.
"""
import pathlib
import sys
from html.parser import HTMLParser

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"
# Elements that have no closing tag.
VOID = {"meta", "link", "img", "br", "hr", "input", "col", "circle", "path", "use"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.open = []
        self.problems = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.open.append(tag)
        self.note_links(attrs)

    def handle_startendtag(self, tag, attrs):
        # A tag written as <use .../> opens and closes at once, so nothing stays open.
        self.note_links(attrs)

    def note_links(self, attrs):
        for name, value in attrs:
            if name == "href" and value:
                self.links.append(value)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.open or self.open[-1] != tag:
            line, _ = self.getpos()
            self.problems.append(f"line {line}: </{tag}> does not close the open element")
        else:
            self.open.pop()


def target(link):
    """The file a link inside the site leads to, or None for a link that leaves it."""
    if not link.startswith("/") or link.startswith("//"):
        return None
    path = link.split("#")[0].split("?")[0].lstrip("/")
    file = SITE / path
    return file / "index.html" if path == "" or path.endswith("/") else file


def check(file):
    problems = []
    data = file.read_bytes()
    for number, line in enumerate(data.split(b"\n"), 1):
        if any(byte > 126 or (byte < 32 and byte != 9) for byte in line):
            problems.append(f"line {number}: a character that is not plain ASCII")
    page = Page()
    page.feed(data.decode("ascii", "replace"))
    problems += page.problems
    if page.open:
        problems.append(f"never closed: {', '.join(page.open)}")
    for link in page.links:
        file_for_link = target(link)
        if file_for_link is not None and not file_for_link.is_file():
            problems.append(f"link {link} leads to nothing")
    return problems


def main():
    pages = sorted(SITE.rglob("*.html"))
    if not (SITE / "index.html").is_file():
        print("FAIL site/index.html is missing")
        return 1
    failed = 0
    for file in pages:
        problems = check(file)
        name = file.relative_to(SITE)
        if problems:
            failed += 1
            for problem in problems:
                print(f"FAIL {name}: {problem}")
        else:
            print(f"ok   {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
