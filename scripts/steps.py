#!/usr/bin/env python3
"""The steps files of the packages repository, shown in code blocks of the pages.

The uninstall commands and the commands of a person who runs the client as themselves are
files of the packages repository (steps/*.sh), because the tests of that repository run those
very files. The install page must show exactly what they run, so a page never holds the text.
It holds a marker where the text goes, inside the code element of the block:

    <pre><code><!-- steps: uninstall-apt --></code></pre>

pages.py replaces the marker by the file steps/uninstall-apt.sh, escaped for HTML. The file
ends with its own newline, so the block ends the way it always did.

The files are taken from the folder STEPS_DIR, or from .steps/ when that is not set.
scripts/fetch-steps.sh fills .steps/ with the files of the main branch of the packages
repository, the same version the change log page is built from.

    steps.py names FOLDER    prints the steps names the pages of FOLDER use, one per line
"""

import html
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MARKER = re.compile(r"<!-- steps: (.+?) -->")
NAME = re.compile(r"^[a-z][a-z0-9-]*$")


class StepsError(Exception):
    """A marker or a steps file that cannot be used."""


def folder():
    """The folder the steps files are read from."""
    return Path(os.environ.get("STEPS_DIR") or ROOT / ".steps")


def check_name(name):
    """The name, when it can be a file name inside the steps folder and part of a URL."""
    if not NAME.match(name):
        raise StepsError(f'"{name}" is not a steps name')
    return name


def block(name, steps_dir):
    """The text of the steps file name.sh, escaped for HTML."""
    if steps_dir is None:
        raise StepsError(f'the steps marker "{name}" is used, but no steps folder was given')
    check_name(name)
    file = steps_dir / f"{name}.sh"
    try:
        text = file.read_text(encoding="utf-8")
    except OSError as err:
        raise StepsError(f"cannot read {file}: {err.strerror} (make steps downloads it)")
    # Only the three characters HTML needs; the quotes stay, as they are in the files.
    return html.escape(text, quote=False)


def fill(line, steps_dir):
    """The line with every steps marker replaced by the text of its steps file."""
    return MARKER.sub(lambda found: block(found.group(1), steps_dir), line)


def names(text):
    """The names of the steps files the text uses, each once, in the order of first use."""
    return list(dict.fromkeys(check_name(name) for name in MARKER.findall(text)))


def names_in(source):
    """The names the HTML pages in the folder use, sorted."""
    found = set()
    for page in source.rglob("*.html"):
        found.update(names(page.read_text(encoding="utf-8")))
    return sorted(found)


def problems(source, built, steps_dir):
    """What is wrong with the code blocks of a built page, one message for each steps file.

    source is the text of the page with its markers, built the text of the finished page.
    Every marker must have become a code block that reads exactly its steps file.
    """
    found = []
    for name, wanted in Counter(MARKER.findall(source)).items():
        try:
            expected = f"<pre><code>{block(name, steps_dir)}</code></pre>"
        except StepsError as err:
            found.append(str(err))
            continue
        have = built.count(expected)
        if have < wanted:
            found.append(f"{name}.sh: {wanted} code blocks must read exactly this file, {have} do")
    if MARKER.search(built):
        found.append("a steps marker is left in the page")
    return found


def main(argv, out=sys.stdout, errors=sys.stderr):
    if len(argv) != 2 or argv[0] != "names":
        errors.write("usage: steps.py names FOLDER\n")
        return 2
    try:
        found = names_in(Path(argv[1]))
    except StepsError as err:
        errors.write(f"steps.py: {err}\n")
        return 1
    out.writelines(f"{name}\n" for name in found)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
