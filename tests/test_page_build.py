#!/usr/bin/env python3
"""Tests of scripts/pages.py, which writes the finished pages from the source pages and the
parts they share.

Run by `make test`. Every test builds in a temporary folder, so none needs the network or leaves
anything behind.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pages  # noqa: E402  (the path above must be set first)


class Folder(unittest.TestCase):
    """A temporary folder with a parts folder, for each test."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.parts = self.root / "parts"
        self.parts.mkdir()

    def part(self, name, text):
        (self.parts / f"{name}.html").write_text(text, encoding="utf-8")

    def expand(self, text):
        return pages.expand(text, self.parts, "page.html")


class TestExpand(Folder):
    def test_text_without_a_marker_is_unchanged(self):
        text = "<p>a</p>\n\n<p>b</p>\n"
        self.assertEqual(self.expand(text), text)

    def test_a_marker_line_is_replaced_by_the_part(self):
        self.part("top", "<header>\n  one\n</header>\n")
        self.assertEqual(
            self.expand("<body>\n<!-- part: top -->\n<main>\n"),
            "<body>\n<header>\n  one\n</header>\n<main>\n",
        )

    def test_a_marker_may_be_used_twice(self):
        self.part("x", "X\n")
        self.assertEqual(self.expand("<!-- part: x -->\n<!-- part: x -->\n"), "X\nX\n")

    def test_a_marker_with_no_part_file_fails_and_says_which(self):
        with self.assertRaises(pages.PartError) as caught:
            self.expand("a\n<!-- part: missing -->\n")
        message = str(caught.exception)
        self.assertIn('page.html:2', message)
        self.assertIn('the part "missing" has no file', message)
        self.assertIn("missing.html", message)

    def test_a_part_name_cannot_leave_the_parts_folder(self):
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: ../secret -->\n")
        self.assertIn("is not a part name", str(caught.exception))


class TestValues(Folder):
    def test_a_value_from_the_marker_fills_the_placeholder(self):
        self.part("w", ".wrap { max-width: {{wrap}}; }\n")
        self.assertEqual(self.expand("<!-- part: w wrap=1120px -->\n"), ".wrap { max-width: 1120px; }\n")

    def test_a_quoted_value_may_hold_spaces(self):
        self.part("w", "a{{extra|}} {}\n")
        self.assertEqual(self.expand('<!-- part: w extra=", b c" -->\n'), "a, b c {}\n")

    def test_the_default_is_used_when_the_marker_gives_no_value(self):
        self.part("w", "{{wrap|760px}}|{{none|}}|\n")
        self.assertEqual(self.expand("<!-- part: w -->\n"), "760px||\n")

    def test_a_placeholder_with_no_default_and_no_value_fails(self):
        self.part("w", "{{wrap}}\n")
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: w -->\n")
        self.assertIn('needs a value for wrap', str(caught.exception))

    def test_a_value_the_part_does_not_use_fails(self):
        self.part("w", "plain\n")
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: w wrap=1px -->\n")
        self.assertIn('does not use: wrap', str(caught.exception))

    def test_an_argument_without_a_value_fails(self):
        self.part("w", "plain\n")
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: w wrap -->\n")
        self.assertIn("name=value", str(caught.exception))

    def test_the_same_value_twice_fails(self):
        self.part("w", "{{a|}}\n")
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: w a=1 a=2 -->\n")
        self.assertIn("twice", str(caught.exception))


class TestFills(Folder):
    PAGE = (
        "<!-- fill: more -->\n"
        "  --x: 1;\n"
        "  --y: 2;\n"
        "<!-- end fill -->\n"
        "<!-- part: root -->\n"
    )

    def test_the_lines_of_a_fill_go_where_the_part_asks(self):
        self.part("root", ":root {\n{{more|}}}\n")
        self.assertEqual(self.expand(self.PAGE), ":root {\n  --x: 1;\n  --y: 2;\n}\n")

    def test_a_fill_the_part_does_not_use_fails(self):
        self.part("root", "plain\n")
        with self.assertRaises(pages.PartError) as caught:
            self.expand(self.PAGE)
        self.assertIn("does not use: more", str(caught.exception))

    def test_a_fill_that_is_never_closed_fails(self):
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- fill: more -->\nx\n")
        self.assertIn("never closed", str(caught.exception))

    def test_a_fill_that_no_part_follows_fails(self):
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- fill: more -->\nx\n<!-- end fill -->\n")
        self.assertIn("no part follows", str(caught.exception))

    def test_an_end_marker_with_no_fill_fails(self):
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- end fill -->\n")
        self.assertIn("no fill is open", str(caught.exception))


class TestCurrent(Folder):
    NAV = '<nav>\n<a href="/a/">A</a>\n<a href="/b/">B</a>\n</nav>\n'

    def test_the_link_to_the_current_page_is_marked(self):
        self.part("nav", self.NAV)
        self.assertEqual(
            self.expand("<!-- part: nav current=/b/ -->\n"),
            '<nav>\n<a href="/a/">A</a>\n<a href="/b/" aria-current="page">B</a>\n</nav>\n',
        )

    def test_without_current_no_link_is_marked(self):
        self.part("nav", self.NAV)
        self.assertEqual(self.expand("<!-- part: nav -->\n"), self.NAV)

    def test_a_current_page_with_no_link_fails(self):
        self.part("nav", self.NAV)
        with self.assertRaises(pages.PartError) as caught:
            self.expand("<!-- part: nav current=/c/ -->\n")
        self.assertIn('no link to /c/', str(caught.exception))


class TestBuild(Folder):
    def setUp(self):
        super().setUp()
        self.source = self.root / "site"
        (self.source / "docs").mkdir(parents=True)
        self.target = self.root / "build"
        self.part("top", "TOP\n")

    def test_html_pages_are_expanded_and_other_files_are_copied_as_they_are(self):
        (self.source / "index.html").write_text("<!-- part: top -->\nhome\n", encoding="utf-8")
        (self.source / "docs" / "index.html").write_text("docs\n", encoding="utf-8")
        (self.source / "docs" / "logo.bin").write_bytes(b"\x00\xff\r\n")
        pages.build(self.source, self.parts, self.target)
        self.assertEqual((self.target / "index.html").read_text(), "TOP\nhome\n")
        self.assertEqual((self.target / "docs" / "index.html").read_text(), "docs\n")
        self.assertEqual((self.target / "docs" / "logo.bin").read_bytes(), b"\x00\xff\r\n")

    def test_the_source_pages_are_not_changed(self):
        page = self.source / "index.html"
        page.write_text("<!-- part: top -->\n", encoding="utf-8")
        pages.build(self.source, self.parts, self.target)
        self.assertEqual(page.read_text(), "<!-- part: top -->\n")

    def test_a_file_left_from_an_earlier_build_is_removed(self):
        self.target.mkdir()
        (self.target / "old.html").write_text("old\n", encoding="utf-8")
        (self.source / "index.html").write_text("new\n", encoding="utf-8")
        pages.build(self.source, self.parts, self.target)
        self.assertFalse((self.target / "old.html").exists())

    def test_a_failing_page_leaves_the_earlier_build_alone_and_names_the_page(self):
        self.target.mkdir()
        (self.target / "index.html").write_text("earlier\n", encoding="utf-8")
        (self.source / "docs" / "index.html").write_text("<!-- part: nope -->\n", encoding="utf-8")
        with self.assertRaises(pages.PartError) as caught:
            pages.build(self.source, self.parts, self.target)
        self.assertIn(str(Path("docs") / "index.html"), str(caught.exception))
        self.assertEqual((self.target / "index.html").read_text(), "earlier\n")


class TestMain(Folder):
    def test_a_build_that_fails_exits_1_with_the_message_on_standard_error(self):
        source = self.root / "site"
        source.mkdir()
        (source / "index.html").write_text("<!-- part: nope -->\n", encoding="utf-8")
        errors = []

        class Stream:
            write = errors.append

        status = pages.main([], source, self.parts, self.root / "build", Stream)
        self.assertEqual(status, 1)
        self.assertIn('the part "nope" has no file', "".join(errors))

    def test_a_build_that_works_exits_0(self):
        source = self.root / "site"
        source.mkdir()
        (source / "index.html").write_text("ok\n", encoding="utf-8")
        status = pages.main([], source, self.parts, self.root / "build", sys.stderr)
        self.assertEqual(status, 0)

    def test_arguments_are_refused(self):
        errors = []

        class Stream:
            write = errors.append

        self.assertEqual(pages.main(["x"], self.root, self.parts, self.root / "b", Stream), 2)
        self.assertIn("usage", "".join(errors))


if __name__ == "__main__":
    unittest.main()
