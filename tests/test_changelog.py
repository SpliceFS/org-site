#!/usr/bin/env python3
"""Tests of scripts/changelog.py, the builder of the change log page.

Run by `make test`. They need no network: the change logs and the release lists are the files
in tests/fixtures, which have the shape of the real ones (see the module text of changelog.py).
The script reads them from one folder, so the tests hand it that folder.
"""

import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "changelog.py"
FIXTURES = ROOT / "tests" / "fixtures"

sys.path.insert(0, str(SCRIPT.parent))
import changelog  # noqa: E402  (the path above must be set first)



def build_page():
    return changelog.build(FIXTURES)


def copy_fixtures(folder, leave_out=()):
    """Copy the change log fixtures into folder (a string), except the files named in
    leave_out. The folders of the fixtures belong to other tests."""
    for source in FIXTURES.iterdir():
        if source.is_file() and source.name not in leave_out:
            shutil.copy(source, Path(folder) / source.name)


def table_body(page):
    return re.search(r"<tbody>.*?</tbody>", page, re.DOTALL).group(0)


def intro(page):
    return re.search(r'<p class="small">(.*?)</p>', page, re.DOTALL).group(1)


def packages_cell(page, version):
    """Return (dates, entries) of the packages cell in the row of one code version."""
    row = re.search(rf'<tr id="v{re.escape(version)}">.*?</tr>', page, re.DOTALL).group(0)
    cell = re.search(r'<td data-label="Packages"[^>]*>(.*?)</td>', row, re.DOTALL).group(1)
    dates = re.findall(r'<span class="when">(.*?)</span>', cell)
    entries = re.findall(r"<li[^>]*>(.*?)</li>", cell)
    return dates, entries


def at(day, hour=0):
    return datetime.datetime(2026, 11, day, hour, tzinfo=datetime.timezone.utc)


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


class ReleaseNotesTest(unittest.TestCase):
    CASES = {
        "keeps the change entries and drops the release lines and the cut comment": (
            "- A change.\n- Release of splicefsd v0.3.0.\n<!-- cut: 2026-11-12T08:59:58Z -->",
            ["A change."],
        ),
        "joins the continuation lines of an entry": ("- One entry\n  on two lines.\n", ["One entry on two lines."]),
        "reads lines that end in carriage return and line feed": (
            "- First.\r\n\r\n- Second.\r\n- Release of splicefs v0.2.0.\r\n",
            ["First.", "Second."],
        ),
        "leaves nothing for notes of release lines only": (
            "- Release of splicefsd v0.2.0.\n- Release of splicefs v0.1.0.\n<!-- cut: 2026-11-10T07:59:58Z -->",
            [],
        ),
        "keeps an entry that only begins like a release line": (
            "- Release of notes is now automatic, for every program.",
            ["Release of notes is now automatic, for every program."],
        ),
        "reads an empty body": ("", []),
        "reads a missing body": (None, []),
    }

    def test_entries(self):
        for name, (body, want) in self.CASES.items():
            with self.subTest(name):
                self.assertEqual(changelog.parse_release_notes("release 1", body), want)

    def test_a_line_that_is_no_entry_is_refused(self):
        with self.assertRaisesRegex(changelog.ChangeLogError, "release 7, notes line 2: a line that is neither"):
            changelog.parse_release_notes("release 7", "- Fine.\nWhat is this?")

    def test_a_body_that_is_no_text_is_refused(self):
        with self.assertRaisesRegex(changelog.ChangeLogError, "release 7: body is not text"):
            changelog.parse_release_notes("release 7", ["- A list."])


class NumberReleasesTest(unittest.TestCase):
    def test_takes_the_releases_with_a_number_tag_and_entries_oldest_first(self):
        got = changelog.parse_number_releases(FIXTURES, "packages.json")
        self.assertEqual(
            got,
            [
                (at(9, 12), 1, ["First change.", "Another first change."]),
                (at(11, 15), 3, ["Third change, which takes two lines."]),
                (at(12, 9), 4, ["Fourth change."]),
            ],
        )

    def test_a_release_list_without_a_number_tag_gives_nothing(self):
        self.assertEqual(changelog.parse_number_releases(FIXTURES, "server.json"), [])

    def test_a_bad_publish_time_is_refused(self):
        bad = [{"tag_name": "3", "published_at": "yesterday", "body": "- A change."}]
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "packages.json").write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(changelog.ChangeLogError, "release 1: published_at"):
                changelog.parse_number_releases(folder, "packages.json")


class PlacementTest(unittest.TestCase):
    CODE = [(at(1), (0, 1, 0)), (at(5), (0, 2, 0)), (at(5, 12), (0, 1, 1))]

    def place(self, changes):
        return changelog.place_packages(changes, self.CODE, (0, 1, 0))

    def test_a_change_goes_to_the_newest_code_version_out_at_that_time(self):
        placed = self.place([(at(6), "2026-11-06", ["late"])])
        self.assertEqual(placed, {(0, 2, 0): [("2026-11-06", ["late"])]})

    def test_a_change_at_the_exact_time_of_a_code_release_goes_to_that_row(self):
        placed = self.place([(at(5), "2026-11-05", ["same time"])])
        self.assertEqual(placed, {(0, 2, 0): [("2026-11-05", ["same time"])]})

    def test_a_change_one_second_before_a_code_release_goes_to_the_row_before(self):
        moment = at(5) - datetime.timedelta(seconds=1)
        placed = self.place([(moment, "2026-11-04", ["just before"])])
        self.assertEqual(placed, {(0, 1, 0): [("2026-11-04", ["just before"])]})

    def test_a_change_before_every_code_release_goes_to_the_lowest_row(self):
        placed = self.place([(at(1) - datetime.timedelta(days=1), "2026-10-31", ["early"])])
        self.assertEqual(placed, {(0, 1, 0): [("2026-10-31", ["early"])]})

    def test_the_row_is_the_highest_version_not_the_latest_release(self):
        placed = self.place([(at(6), "2026-11-06", ["x"])])
        self.assertEqual(list(placed), [(0, 2, 0)])

    def test_several_changes_in_a_row_are_listed_newest_first(self):
        changes = [
            (at(6), "2026-11-06", ["older"]),
            (at(8), "2026-11-08", ["newer"]),
            (at(7), "2026-11-07", ["middle"]),
        ]
        self.assertEqual(
            self.place(changes)[(0, 2, 0)],
            [("2026-11-08", ["newer"]), ("2026-11-07", ["middle"]), ("2026-11-06", ["older"])],
        )

    def test_changes_at_the_same_time_keep_the_order_they_were_given_reversed(self):
        changes = [(at(6), "2026-11-06", ["first"]), (at(6), "2026-11-06", ["second"])]
        self.assertEqual(
            self.place(changes)[(0, 2, 0)],
            [("2026-11-06", ["second"]), ("2026-11-06", ["first"])],
        )


class BuildFromReleasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = build_page()

    def test_releases_are_in_the_row_of_the_newest_code_version_out_at_the_time(self):
        dates, entries = packages_cell(self.page, "0.3.0")
        self.assertEqual(dates, ["2026-11-12", "2026-11-11"])
        self.assertEqual(entries, ["Fourth change.", "Third change, which takes two lines."])

    def test_a_row_lists_releases_and_older_history_together_newest_first(self):
        dates, entries = packages_cell(self.page, "0.2.0")
        self.assertEqual(dates, ["2026-11-09", "2026-11-06"])
        self.assertEqual(
            entries,
            ["First change.", "Another first change.", "Second history change of the packages."],
        )

    def test_the_release_lines_and_the_cut_comment_do_not_reach_the_page(self):
        for text in ("Release of", "cut:", "<!--"):
            self.assertNotIn(text, table_body(self.page))

    def test_releases_that_are_no_number_or_no_publication_add_nothing(self):
        for text in ("A draft", "leading zero", "no number"):
            self.assertNotIn(text, table_body(self.page))

    def test_the_intro_says_where_a_packages_release_goes(self):
        self.assertIn("newest server or client version", intro(self.page))


def run_script(*arguments):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, arguments)],
        capture_output=True,
        text=True,
        check=False,
    )


class TemplatePartsTest(unittest.TestCase):
    def test_the_page_has_the_shared_menu_and_footer(self):
        page = build_page()
        self.assertEqual(page.count('<nav class="nav"'), 1)
        self.assertIn('<a href="/changelog/" aria-current="page">Change log</a>', page)
        self.assertIn("SpliceFS is open source under the MIT license.", page)

    def test_a_marker_with_no_part_file_stops_the_build_and_says_which(self):
        with tempfile.TemporaryDirectory() as folder:
            template = Path(folder) / "changelog-page.html"
            template.write_text("<!-- part: missing -->\n<!-- ROWS -->\n", encoding="utf-8")
            original = changelog.TEMPLATE
            changelog.TEMPLATE = template
            self.addCleanup(setattr, changelog, "TEMPLATE", original)
            with self.assertRaises(changelog.ChangeLogError) as caught:
                changelog.build(FIXTURES)
        self.assertIn('the part "missing" has no file', str(caught.exception))


class CommandLineTest(unittest.TestCase):
    def test_prints_the_page_for_the_folder(self):
        result = run_script(FIXTURES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, build_page())

    def test_a_file_that_cannot_be_read_stops_the_build(self):
        with tempfile.TemporaryDirectory() as folder:
            copy_fixtures(folder, leave_out=("packages.json",))
            result = run_script(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot read the file", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_one_argument_is_needed(self):
        for arguments in ((), (FIXTURES, FIXTURES)):
            with self.subTest(arguments=arguments):
                result = run_script(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage: changelog.py FOLDER", result.stderr)
                self.assertEqual(result.stdout, "")


class InputFolderTest(unittest.TestCase):
    """Only the files of the input folder are read, never a path that leaves it."""

    def test_reads_a_file_of_the_folder(self):
        text = changelog.read_input(FIXTURES, "server.md")
        self.assertEqual(text, (FIXTURES / "server.md").read_text(encoding="utf-8"))

    def test_a_name_that_leaves_the_folder_is_refused(self):
        for name in ("../test_changelog.py", "/etc/hosts", "sub/../../test_changelog.py"):
            with self.subTest(name):
                with self.assertRaisesRegex(changelog.ChangeLogError, "outside the input folder"):
                    changelog.read_input(FIXTURES, name)

    def test_a_link_that_points_out_of_the_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as elsewhere:
            copy_fixtures(folder, leave_out=("server.md",))
            secret = Path(elsewhere) / "secret.md"
            secret.write_text("## [9.9.9] - 2026-11-01\n\n- Not for the page.\n", encoding="utf-8")
            (Path(folder) / "server.md").symlink_to(secret)
            with self.assertRaisesRegex(changelog.ChangeLogError, "outside the input folder"):
                changelog.parse(folder, "server.md")
            result = run_script(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the input folder", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_a_link_inside_the_folder_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            copy_fixtures(folder, leave_out=("client.md",))
            (Path(folder) / "client.md").symlink_to(Path(folder) / "server.md")
            self.assertIn((0, 3, 0), changelog.parse(folder, "client.md"))

    def test_a_folder_that_is_given_as_a_relative_path_is_read(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "fixtures"],
            cwd=FIXTURES.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, build_page())


if __name__ == "__main__":
    unittest.main()
