#!/usr/bin/env python3
"""Build the change log page of splicefs.org from the three CHANGELOG.md files.

Usage: scripts/changelog.py SERVER.md CLIENT.md PACKAGES.md > site/changelog/index.html

Each file has one heading per version:

    ## [0.3.2] - 2026-11-13

    - A change. A second line of the same change starts with two spaces.

The page is the template scripts/changelog-page.html with the marker <!-- ROWS -->
replaced by one table row per version. A version found in only some of the files gets an
empty cell for the others. Exit status 1 and a message on standard error mean that a file
could not be read as a change log, so a broken file never turns into a quietly wrong page.
"""

import datetime
import html
import re
import sys
import textwrap
from pathlib import Path

TEMPLATE = Path(__file__).resolve().with_name("changelog-page.html")
MARKER = "<!-- ROWS -->"
PARTS = ("Server", "Client", "Packages")

HEADING = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\] - (\d{4}-\d{2}-\d{2})\s*$")
# Anything that is meant to be a version heading. If one of these does not match HEADING,
# it is a typo, and the file is refused instead of the version being dropped from the page.
VERSION_LIKE = re.compile(r"^##\s*(\[|v?\d)")
UNRELEASED = re.compile(r"^##\s+Unreleased\b", re.IGNORECASE)
CODE = re.compile(r"`([^`]+)`")


class ChangeLogError(Exception):
    pass


def parse(path):
    """Return {(major, minor, patch): (date, [bullet, ...])} for one change log file."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as err:
        raise ChangeLogError(f"{path}: cannot read the file: {err}")

    versions = {}
    current = None  # the bullet list of the version being read, None outside a version
    for number, line in enumerate(lines, 1):
        where = f"{path}:{number}"
        if line.startswith("## "):
            match = HEADING.match(line)
            if match:
                key = tuple(int(part) for part in match.group(1, 2, 3))
                date = match.group(4)
                try:
                    datetime.date.fromisoformat(date)
                except ValueError:
                    raise ChangeLogError(f"{where}: the date {date} does not exist: {line}")
                if key in versions:
                    raise ChangeLogError(f"{where}: this version is listed twice: {line}")
                current = []
                versions[key] = (date, current)
            elif VERSION_LIKE.match(line):
                raise ChangeLogError(
                    f"{where}: looks like a version heading but is not "
                    f"'## [X.Y.Z] - YYYY-MM-DD': {line}"
                )
            else:
                # "## Unreleased" and any other heading: its bullets are not part of a release.
                current = None
            continue
        if current is None or not line.strip():
            continue
        if line.startswith("- "):
            current.append(line[2:].strip())
        elif line.startswith("  ") and current:
            current[-1] += " " + line.strip()
        else:
            raise ChangeLogError(f"{where}: a line that is neither a bullet ('- ') nor its continuation (two spaces): {line}")

    if not versions:
        raise ChangeLogError(f"{path}: no version heading '## [X.Y.Z] - YYYY-MM-DD' found")
    return versions


def ascii_only(text):
    """Replace every non-ASCII character by a numeric entity, the site checker refuses them."""
    return text.encode("ascii", "xmlcharrefreplace").decode("ascii")


def render_bullet(text):
    escaped = html.escape(text, quote=True)
    escaped = CODE.sub(r"<code>\1</code>", escaped)
    css = ' class="internal"' if text.startswith("Internal: ") else ""
    return f"<li{css}>{ascii_only(escaped)}</li>"


def render_cell(part, entry):
    if entry is None:
        return f'        <td data-label="{part}" class="none"></td>'
    date, bullets = entry
    out = [f'        <td data-label="{part}">', f'          <span class="when">{date}</span>']
    if bullets:
        out.append("          <ul>")
        out.extend(f"            {render_bullet(bullet)}" for bullet in bullets)
        out.append("          </ul>")
    out.append("        </td>")
    return "\n".join(out)


def render_row(key, entries):
    name = ".".join(str(part) for part in key)
    out = [
        f'      <tr id="v{name}">',
        f'        <th scope="row"><a href="#v{name}">{name}</a></th>',
    ]
    out.extend(render_cell(part, entry) for part, entry in zip(PARTS, entries))
    out.append("      </tr>")
    return "\n".join(out)


def build(paths):
    logs = [parse(path) for path in paths]
    # Sorted as numbers, so 0.10.0 comes before 0.9.0.
    keys = sorted(set().union(*logs), reverse=True)
    rows = [render_row(key, [log.get(key) for log in logs]) for key in keys]
    # The rows are written for the page's indentation, two steps deeper than the tbody tag.
    rows = [textwrap.indent(row, "  ") for row in rows]

    try:
        template = TEMPLATE.read_text(encoding="utf-8")
    except OSError as err:
        raise ChangeLogError(f"{TEMPLATE}: cannot read the template: {err}")
    if template.count(MARKER) != 1:
        raise ChangeLogError(f"{TEMPLATE}: the marker {MARKER} must occur exactly once")
    return ascii_only(template.replace(MARKER, "\n".join(rows).lstrip()))


def main(argv):
    if len(argv) != 4:
        sys.stderr.write("usage: changelog.py SERVER.md CLIENT.md PACKAGES.md > index.html\n")
        return 2
    try:
        page = build(argv[1:])
    except ChangeLogError as err:
        sys.stderr.write(f"changelog.py: {err}\n")
        return 1
    sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
