#!/usr/bin/env python3
"""Tests of scripts/changelog.py, the builder of the change log page.

Run by `make test`. They need no network: the change logs and the release lists are the files
in tests/fixtures, which have the shape of the real ones (see the module text of changelog.py).
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "changelog.py"
FIXTURES = ROOT / "tests" / "fixtures"

sys.path.insert(0, str(SCRIPT.parent))
import changelog  # noqa: E402  (the path above must be set first)

LOGS = [FIXTURES / f"{part}.md" for part in ("server", "client", "packages")]
RELEASES = [FIXTURES / f"{part}.json" for part in ("server", "client", "packages")]


def build_page():
    return changelog.build(LOGS, RELEASES)


def packages_cell(page, version):
    """Return (dates, entries) of the packages cell in the row of one code version."""
    row = re.search(rf'<tr id="v{re.escape(version)}">.*?</tr>', page, re.DOTALL).group(0)
    cell = re.search(r'<td data-label="Packages"[^>]*>(.*?)</td>', row, re.DOTALL).group(1)
    dates = re.findall(r'<span class="when">(.*?)</span>', cell)
    entries = re.findall(r"<li[^>]*>(.*?)</li>", cell)
    return dates, entries


class BuildFromHistoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = build_page()

    def test_one_row_per_code_version_newest_first(self):
        rows = re.findall(r'<tr id="v([0-9.]+)">', self.page)
        self.assertEqual(rows, ["0.3.0", "0.2.0", "0.1.0"])

    def test_history_entry_is_in_the_row_current_when_it_went_out(self):
        _dates, first_row = packages_cell(self.page, "0.1.0")
        _dates, second_row = packages_cell(self.page, "0.2.0")
        self.assertEqual(first_row, ["First history change of the packages."])
        self.assertIn("Second history change of the packages.", second_row)

    def test_history_date_is_the_one_of_the_change_log_heading(self):
        dates, _entries = packages_cell(self.page, "0.1.0")
        self.assertEqual(dates, ["2026-11-03"])


class CommandLineTest(unittest.TestCase):
    def run_script(self, releases):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, LOGS), *map(str, releases)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_prints_the_page(self):
        result = self.run_script(RELEASES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, build_page())

    def test_a_file_that_cannot_be_read_stops_the_build(self):
        result = self.run_script([RELEASES[0], RELEASES[1], FIXTURES / "missing.json"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read the file", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
