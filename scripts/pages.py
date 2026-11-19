#!/usr/bin/env python3
"""Writes the finished pages into build/ from the source pages in site/ and the parts in parts/.

The pages of the website all start and end the same way: the head lines, the style rules every
page uses, the logo with the menu, and the footer. Each of those is written once, as a file in
parts/. A source page holds a marker line where a part goes:

    <!-- part: header current=/install/ -->

The line is replaced by the file parts/header.html. After the part name come values, written
name=value, with the value in double quotes when it holds spaces. A part holds the places for
them as {{name}} (the marker must give a value) or {{name|default}} (it may; the default is
used otherwise, and may be empty). Several lines are given as a fill, written before the marker
it belongs to; its lines become the value of the name:

    <!-- fill: light-extra -->
      --one: 1;
    <!-- end fill -->
    <!-- part: style-base -->

The value current is the path of the page the visitor is on. The link in the part that leads to
that path gets aria-current="page", so the menu part is one plain list of links for every page.

Anything that fails, a part with no file, a value the part does not use, a fill that is never
closed, stops the build with a message that names the page and the line, so a typo never
publishes a page with a marker still in it. The source pages are never changed. Only .html files
are expanded; every other file in site/ is copied as it is. The folder build/ is replaced as a
whole, and only once every page has been built, so a failed build leaves the last one in place.
The change log page is built by changelog.py, which expands its template with the same parts.
"""

import re
import shlex
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PARTS = ROOT / "parts"
BUILD = ROOT / "build"

PART_MARKER = re.compile(r"^<!-- part: (.+) -->$")
FILL_START = re.compile(r"^<!-- fill: (\S+) -->$")
FILL_END = "<!-- end fill -->"
NAME = re.compile(r"^[a-z][a-z0-9-]*$")
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9-]*)(?:\|([^}]*))?\}\}")


class PartError(Exception):
    """A marker, a value or a fill that cannot be used."""


def read_arguments(text, where):
    """The part name and the name=value pairs of a marker, as (name, {name: value})."""
    try:
        words = shlex.split(text)
    except ValueError as err:
        raise PartError(f"{where}: cannot read the marker: {err}")
    values = {}
    for word in words[1:]:
        key, separator, value = word.partition("=")
        if not separator or not NAME.match(key):
            raise PartError(f'{where}: "{word}" is not written name=value')
        if key in values:
            raise PartError(f"{where}: {key} is given twice")
        values[key] = value
    return words[0], values


def mark_current(body, path, where, name):
    """The part with aria-current on the one link that leads to path."""
    link = f'<a href="{path}">'
    if body.count(link) != 1:
        raise PartError(f'{where}: the part "{name}" has no link to {path}, or more than one')
    return body.replace(link, f'<a href="{path}" aria-current="page">')


def render(name, values, fills, parts, where):
    """The text of one part with its values in place, without the last newline."""
    if not NAME.match(name):
        raise PartError(f'{where}: "{name}" is not a part name')
    file = parts / f"{name}.html"
    if not file.is_file():
        raise PartError(f'{where}: the part "{name}" has no file {file}')
    body = file.read_text(encoding="utf-8")
    given = {key: value for key, value in values.items() if key != "current"}
    both = sorted(given.keys() & fills.keys())
    if both:
        raise PartError(f"{where}: {', '.join(both)} is given as a value and as a fill")
    given.update(fills)
    unused = sorted(given.keys() - {found.group(1) for found in PLACEHOLDER.finditer(body)})
    if unused:
        raise PartError(f'{where}: the part "{name}" does not use: {", ".join(unused)}')

    def put(found):
        key, default = found.group(1), found.group(2)
        if key in given:
            return given[key]
        if default is None:
            raise PartError(f'{where}: the part "{name}" needs a value for {key}')
        return default

    body = PLACEHOLDER.sub(put, body)
    if "current" in values:
        body = mark_current(body, values["current"], where, name)
    return body.removesuffix("\n")


def expand(text, parts, origin):
    """The text with every part marker replaced. origin names the text in messages."""
    out = []
    fills = {}
    open_fill = None  # (name, first line number, lines) while a fill is being read
    for number, line in enumerate(text.split("\n"), 1):
        where = f"{origin}:{number}"
        if open_fill is not None:
            if line == FILL_END:
                key, _, lines = open_fill
                fills[key] = "".join(f"{each}\n" for each in lines)
                open_fill = None
            else:
                open_fill[2].append(line)
            continue
        if line == FILL_END:
            raise PartError(f"{where}: {FILL_END} but no fill is open")
        start = FILL_START.match(line)
        if start:
            if start.group(1) in fills:
                raise PartError(f"{where}: the fill {start.group(1)} is written twice")
            open_fill = (start.group(1), number, [])
            continue
        marker = PART_MARKER.match(line)
        if marker:
            name, values = read_arguments(marker.group(1), where)
            out.append(render(name, values, fills, parts, where))
            fills = {}
        else:
            if fills and line.strip():
                raise PartError(f"{where}: a fill is written, but no part follows it")
            out.append(line)
    if open_fill is not None:
        raise PartError(f"{origin}:{open_fill[1]}: the fill {open_fill[0]} is never closed")
    if fills:
        raise PartError(f"{origin}: a fill is written, but no part follows it")
    return "\n".join(out)


def build_files(source, parts):
    """Every file of the source folder as (path relative to it, bytes), pages expanded."""
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        data = path.read_bytes()
        if path.suffix == ".html":
            data = expand(data.decode("utf-8"), parts, str(relative)).encode("utf-8")
        files.append((relative, data))
    return files


def build(source, parts, target):
    """Replaces the target folder with the built source folder."""
    files = build_files(source, parts)
    shutil.rmtree(target, ignore_errors=True)
    for relative, data in files:
        file = target / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)


def main(argv, source=SITE, parts=PARTS, target=BUILD, errors=sys.stderr):
    if argv:
        errors.write("usage: pages.py\n")
        return 2
    try:
        build(source, parts, target)
    except PartError as err:
        errors.write(f"pages.py: {err}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
