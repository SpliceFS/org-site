#!/usr/bin/env python3
"""Build the change log page of splicefs.org from the three CHANGELOG.md files.

Usage:
    scripts/changelog.py SERVER.md CLIENT.md PACKAGES.md SERVER.json CLIENT.json PACKAGES.json
        > site/changelog/index.html

Each change log has one heading per version:

    ## [0.3.2] - 2026-11-13

    - A change. A second line of the same change starts with two spaces.

Each JSON file is the answer of the GitHub API for the releases of that repository
(GET /repos/SpliceFS/<repo>/releases?per_page=100). Only tag_name and published_at are used.

The page is the template scripts/changelog-page.html with the marker <!-- ROWS --> replaced
by one table row per version of the code, that is per version found in the server or the
client change log. The packages repository has version numbers of its own, so they make no
row. Each packaging change is put into the row of the code version that was current when it
went out: the highest code version released at or before the time of the packaging change.
A version without a release in the JSON file counts as released at the start of the date in
its heading, but never before the next lower version of the same repository went out (and
then one second after it). Exit status 1 and a message on standard error mean that a file could
not be read, so a broken file never turns into a quietly wrong page.
"""

import datetime
import html
import json
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
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TIME = "%Y-%m-%dT%H:%M:%SZ"


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


def parse_releases(path):
    """Return {(major, minor, patch): publish time} from the GitHub answer for one repository."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise ChangeLogError(f"{path}: cannot read the file: {err}")
    try:
        data = json.loads(text)
    except ValueError as err:
        raise ChangeLogError(f"{path}: not valid JSON: {err}")
    if not isinstance(data, list):
        raise ChangeLogError(f"{path}: expected a list of releases, found {type(data).__name__}")

    times = {}
    for number, release in enumerate(data, 1):
        where = f"{path}: release {number}"
        if not isinstance(release, dict) or not isinstance(release.get("tag_name"), str):
            raise ChangeLogError(f"{where}: no tag_name, this is not a list of GitHub releases")
        match = TAG.match(release["tag_name"])
        if not match:
            # A tag that is not a version number has no entry in any change log.
            continue
        published = release.get("published_at")
        if published is None:
            # A draft has not gone out yet.
            continue
        try:
            moment = datetime.datetime.strptime(published, TIME)
        except (TypeError, ValueError):
            raise ChangeLogError(
                f"{where}: published_at {published!r} is not a time like 2026-11-13T20:09:24Z"
            )
        key = tuple(int(part) for part in match.groups())
        if key in times:
            raise ChangeLogError(f"{where}: the release {release['tag_name']} is listed twice")
        times[key] = moment.replace(tzinfo=datetime.timezone.utc)
    return times


def version_times(log, released):
    """Return {version: when it went out} for every version of one change log.

    A version without a release gets the start of its heading date (UTC), but never a time
    before the next lower version of the same repository, or it would look older than a
    version that was released before it. The versions are worked through from the lowest, so a
    chain of versions without a release stays in order, one second apart at the least.
    """
    times = {}
    previous = None
    for key in sorted(log):
        if key in released:
            times[key] = released[key]
        else:
            moment = datetime.datetime.fromisoformat(f"{log[key][0]}T00:00:00+00:00")
            if previous is not None:
                moment = max(moment, previous + datetime.timedelta(seconds=1))
            times[key] = moment
        previous = times[key]
    return times


def place_packages(log, times, code_releases, lowest):
    """Return {code version: [(date, bullets), ...]} for the packaging changes, oldest first.

    The date is the one in the change log heading, so the page agrees with the change log file.
    """
    changes = sorted((times[key], key, date, bullets) for key, (date, bullets) in log.items())
    placed = {}
    for moment, _key, date, bullets in changes:
        current = [code for when, code in code_releases if when <= moment]
        row = max(current) if current else lowest
        placed.setdefault(row, []).append((date, bullets))
    return placed


def ascii_only(text):
    """Replace every non-ASCII character by a numeric entity, the site checker refuses them."""
    return text.encode("ascii", "xmlcharrefreplace").decode("ascii")


def render_bullet(text):
    escaped = html.escape(text, quote=True)
    escaped = CODE.sub(r"<code>\1</code>", escaped)
    css = ' class="internal"' if text.startswith("Internal: ") else ""
    return f"<li{css}>{ascii_only(escaped)}</li>"


def render_cell(part, entries):
    if not entries:
        return f'        <td data-label="{part}" class="none"></td>'
    out = [f'        <td data-label="{part}">']
    for date, bullets in entries:
        out.append(f'          <span class="when">{date}</span>')
        if bullets:
            out.append("          <ul>")
            out.extend(f"            {render_bullet(bullet)}" for bullet in bullets)
            out.append("          </ul>")
    out.append("        </td>")
    return "\n".join(out)


def render_row(key, cells):
    name = ".".join(str(part) for part in key)
    out = [
        f'      <tr id="v{name}">',
        f'        <th scope="row"><a href="#v{name}">{name}</a></th>',
    ]
    out.extend(render_cell(part, entries) for part, entries in zip(PARTS, cells))
    out.append("      </tr>")
    return "\n".join(out)


def build(log_paths, release_paths):
    server, client, packages = [parse(path) for path in log_paths]
    server_released, client_released, packages_released = [
        parse_releases(path) for path in release_paths
    ]
    # Sorted as numbers, so 0.10.0 comes before 0.9.0. Only the code makes rows.
    keys = sorted(set(server) | set(client), reverse=True)
    code_releases = [
        (when, key)
        for log, released in ((server, server_released), (client, client_released))
        for key, when in version_times(log, released).items()
    ]
    placed = place_packages(
        packages, version_times(packages, packages_released), code_releases, keys[-1]
    )
    rows = [
        render_row(
            key,
            [
                [server[key]] if key in server else [],
                [client[key]] if key in client else [],
                placed.get(key, []),
            ],
        )
        for key in keys
    ]
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
    if len(argv) != 7:
        sys.stderr.write(
            "usage: changelog.py SERVER.md CLIENT.md PACKAGES.md "
            "SERVER.json CLIENT.json PACKAGES.json > index.html\n"
        )
        return 2
    try:
        page = build(argv[1:4], argv[4:7])
    except ChangeLogError as err:
        sys.stderr.write(f"changelog.py: {err}\n")
        return 1
    sys.stdout.write(page)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
