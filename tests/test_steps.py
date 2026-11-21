#!/usr/bin/env python3
"""Tests of scripts/steps.py, which fills the code blocks of the pages from the steps files of
the packages repository, and of the way pages.py and the page check use it.

Run by `make test`. The steps files are the ones in tests/fixtures/steps, so no test needs the
network.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pages  # noqa: E402  (the path above must be set first)
import steps  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "steps"
APT = (FIXTURES / "uninstall-apt.sh").read_text(encoding="utf-8")
APT_ESCAPED = APT.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
START = (FIXTURES / "user-mode-start.sh").read_text(encoding="utf-8")


class _Stream:
    """Collects what is written, in place of standard output or error."""

    def __init__(self, into):
        self.write = into.append
        self.writelines = into.extend


def block(name):
    return f"<pre><code><!-- steps: {name} --></code></pre>"


def filled(text):
    return f"<pre><code>{text}</code></pre>"


class TestFill(unittest.TestCase):
    def test_a_marker_is_replaced_by_the_text_of_its_steps_file(self):
        self.assertEqual(steps.fill(block("uninstall-apt"), FIXTURES), filled(APT_ESCAPED))

    def test_the_text_is_escaped_for_html_and_nothing_else_is_changed(self):
        self.assertIn("&amp;&amp; echo", APT_ESCAPED)
        self.assertIn("&gt; /dev/null", APT_ESCAPED)
        self.assertEqual(
            steps.fill("<!-- steps: user-mode-start -->", FIXTURES),
            START.replace("<", "&lt;").replace(">", "&gt;"),
        )
        self.assertIn('"https://east.example.com/api"', steps.fill("<!-- steps: user-mode-start -->", FIXTURES))

    def test_the_file_ends_with_its_own_newline_and_the_page_adds_none(self):
        self.assertTrue(APT.endswith("\n"))
        self.assertEqual(steps.fill(block("uninstall-apt"), FIXTURES).count("\n"), APT.count("\n"))

    def test_a_line_without_a_marker_is_unchanged(self):
        self.assertEqual(steps.fill("<p>a &amp; b</p>", FIXTURES), "<p>a &amp; b</p>")

    def test_a_steps_file_that_is_missing_is_refused_and_named(self):
        with self.assertRaises(steps.StepsError) as caught:
            steps.fill(block("uninstall-nope"), FIXTURES)
        self.assertIn("uninstall-nope.sh", str(caught.exception))

    def test_a_name_that_leaves_the_steps_folder_is_refused(self):
        with self.assertRaises(steps.StepsError) as caught:
            steps.fill("<!-- steps: ../secret -->", FIXTURES)
        self.assertIn("is not a steps name", str(caught.exception))

    def test_no_steps_folder_is_refused(self):
        with self.assertRaises(steps.StepsError) as caught:
            steps.fill(block("uninstall-apt"), None)
        self.assertIn("no steps folder", str(caught.exception))


class TestNames(unittest.TestCase):
    def test_the_names_of_a_text_come_once_each_in_the_order_of_their_first_marker(self):
        text = f"{block('b')}\n<p>x</p>\n{block('a')}\n{block('b')}\n"
        self.assertEqual(steps.names(text), ["b", "a"])

    def test_a_text_without_a_marker_has_no_names(self):
        self.assertEqual(steps.names("<p>none</p>\n"), [])

    def test_a_name_that_is_no_steps_name_is_refused(self):
        with self.assertRaises(steps.StepsError):
            steps.names("<!-- steps: a;b -->")

    def test_the_command_prints_the_names_one_per_line_and_refuses_a_bad_name(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "index.html"
            page.write_text(block("b") + block("a"), encoding="utf-8")
            out, errors = [], []
            self.assertEqual(steps.main(["names", folder], _Stream(out), _Stream(errors)), 0)
            self.assertEqual("".join(out), "a\nb\n")
            page.write_text("<!-- steps: ../x -->", encoding="utf-8")
            self.assertEqual(steps.main(["names", folder], _Stream(out), _Stream(errors)), 1)
            self.assertIn("is not a steps name", "".join(errors))

    def test_other_arguments_are_refused(self):
        errors = []
        self.assertEqual(steps.main(["x"], _Stream([]), _Stream(errors)), 2)
        self.assertIn("usage", "".join(errors))

    def test_the_names_of_a_folder_of_pages_are_those_of_all_its_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "one").mkdir()
            (Path(folder) / "one" / "index.html").write_text(block("b"), encoding="utf-8")
            (Path(folder) / "index.html").write_text(block("a") + block("b"), encoding="utf-8")
            (Path(folder) / "style.css").write_text(block("ignored"), encoding="utf-8")
            self.assertEqual(steps.names_in(Path(folder)), ["a", "b"])


class TestProblems(unittest.TestCase):
    SOURCE = f"<p>a</p>\n{block('uninstall-apt')}\n{block('uninstall-apt')}\n"

    def built(self, *texts):
        return "\n".join(filled(text) for text in texts)

    def test_a_page_whose_blocks_read_their_steps_files_has_no_problem(self):
        built = self.built(APT_ESCAPED, APT_ESCAPED)
        self.assertEqual(steps.problems(self.SOURCE, built, FIXTURES), [])

    def test_a_block_that_differs_from_its_steps_file_is_a_problem_and_names_the_file(self):
        built = self.built(APT_ESCAPED, APT_ESCAPED.replace("remove", "delete"))
        found = steps.problems(self.SOURCE, built, FIXTURES)
        self.assertEqual(len(found), 1)
        self.assertIn("uninstall-apt.sh", found[0])

    def test_a_block_that_is_missing_is_a_problem(self):
        found = steps.problems(self.SOURCE, self.built(APT_ESCAPED), FIXTURES)
        self.assertEqual(len(found), 1)
        self.assertIn("uninstall-apt.sh", found[0])

    def test_a_steps_file_that_cannot_be_read_is_a_problem(self):
        found = steps.problems(block("uninstall-nope"), "", FIXTURES)
        self.assertEqual(len(found), 1)
        self.assertIn("uninstall-nope.sh", found[0])

    def test_a_marker_left_in_a_built_page_is_a_problem(self):
        found = steps.problems("", block("uninstall-apt"), FIXTURES)
        self.assertEqual(len(found), 1)
        self.assertIn("marker", found[0])

    def test_a_marker_outside_a_code_block_does_not_count_as_a_block(self):
        found = steps.problems("<!-- steps: uninstall-apt -->", APT_ESCAPED, FIXTURES)
        self.assertEqual(len(found), 1)


class TestPages(unittest.TestCase):
    def test_a_page_is_built_with_its_blocks_filled_and_the_source_keeps_the_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "site").mkdir()
            (root / "parts").mkdir()
            source = root / "site" / "index.html"
            source.write_text(f"<p>x</p>\n{block('uninstall-apt')}\n", encoding="utf-8")
            pages.build(root / "site", root / "parts", root / "build", FIXTURES)
            built = (root / "build" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(built, f"<p>x</p>\n{filled(APT_ESCAPED)}\n")
            self.assertIn("<!-- steps: uninstall-apt -->", source.read_text(encoding="utf-8"))

    def test_a_marker_whose_file_is_missing_stops_the_build_and_names_the_page_and_line(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "parts").mkdir()
            with self.assertRaises(pages.PartError) as caught:
                pages.expand(f"a\n{block('uninstall-nope')}\n", root / "parts", "page.html", FIXTURES)
            self.assertIn("page.html:2", str(caught.exception))
            self.assertIn("uninstall-nope.sh", str(caught.exception))

    def test_a_page_may_use_parts_and_steps_markers_together(self):
        with tempfile.TemporaryDirectory() as folder:
            parts = Path(folder)
            (parts / "top.html").write_text("TOP\n", encoding="utf-8")
            text = f"<!-- part: top -->\n{block('uninstall-apt')}\n"
            self.assertEqual(pages.expand(text, parts, "page.html", FIXTURES), f"TOP\n{filled(APT_ESCAPED)}\n")


class TestFetchScript(unittest.TestCase):
    def test_with_a_steps_folder_given_nothing_is_downloaded(self):
        env = dict(os.environ, STEPS_DIR=str(FIXTURES))
        done = subprocess.run(
            [str(ROOT / "scripts" / "fetch-steps.sh")], env=env, capture_output=True, text=True, check=False
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(str(FIXTURES), done.stdout)


if __name__ == "__main__":
    unittest.main()
