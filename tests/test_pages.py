"""Rules every page of the site keeps, checked on the finished pages.

The pages are built into a temporary folder first, the way make build does it, so what is
checked is what a visitor gets. The change log page is built from the files in tests/fixtures.
"""

import atexit
import pathlib
import re
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import changelog  # noqa: E402  (the path above must be set first)
import pages  # noqa: E402
import steps  # noqa: E402

BUILT = pathlib.Path(tempfile.mkdtemp())
atexit.register(shutil.rmtree, BUILT, ignore_errors=True)
# The steps files of the packages repository: the fixtures stand in for the download.
STEPS = ROOT / "tests" / "fixtures" / "steps"
pages.build(pages.SITE, pages.PARTS, BUILT, STEPS)
(BUILT / "changelog").mkdir()
(BUILT / "changelog" / "index.html").write_text(
    changelog.build(ROOT / "tests" / "fixtures"), encoding="utf-8"
)
# The built pages, and the sources they come from: the pages of the site folder and the
# template of the change log page.
PAGES = sorted(BUILT.glob("**/*.html"))
SOURCES = sorted(pages.SITE.glob("**/*.html")) + [ROOT / "scripts" / "changelog-page.html"]
LOGO = re.compile(r'<a class="mark" href="/">')
INSTALL_PAGE = BUILT / "install" / "index.html"
NAV_INSTALL = re.compile(r'<nav class="nav"[^>]*>.*?<a href="([^"]*)"[^>]*>Install</a>', re.DOTALL)
# One section per operating system, each with its own steps; the page has one chooser.
SYSTEM = re.compile(r'<section class="os" id="(\w+)" data-os="\1">(.*?)<!-- end \1 -->', re.DOTALL)
STEP = re.compile(r'<section class="one" id="\w+-\w+">(.*?)</section>', re.DOTALL)
CHOOSER = re.compile(r'class="chooser"')
SYSTEM_BUTTON = re.compile(r'<button type="button" class="seg" data-os="(\w+)"')


class TestPages(unittest.TestCase):
    def test_every_page_has_pages(self):
        self.assertGreater(len(PAGES), 1)

    def test_the_logo_leads_to_the_home_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(BUILT))):
                self.assertRegex(page.read_text(encoding="utf-8"), LOGO)

    def test_the_install_link_of_the_menu_leads_to_the_install_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(BUILT))):
                found = NAV_INSTALL.search(page.read_text(encoding="utf-8"))
                self.assertIsNotNone(found)
                self.assertEqual(found.group(1), "/install/")


    def test_no_marker_is_left_in_a_built_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(BUILT))):
                self.assertNotRegex(page.read_text(encoding="utf-8"), r"<!-- (part|fill|end fill|steps)\b")

    def test_every_page_has_the_menu_and_the_footer(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(BUILT))):
                text = page.read_text(encoding="utf-8")
                self.assertEqual(text.count('<nav class="nav"'), 1)
                self.assertIn("SpliceFS is open source under the MIT license.", text)

    def test_every_filled_code_block_reads_its_steps_file(self):
        for page in PAGES:
            source = pages.SITE / page.relative_to(BUILT)
            if not source.is_file():
                continue
            with self.subTest(page=str(page.relative_to(BUILT))):
                found = steps.problems(
                    source.read_text(encoding="utf-8"), page.read_text(encoding="utf-8"), STEPS
                )
                self.assertEqual(found, [])

    def test_the_current_page_is_the_only_one_marked_in_the_menu(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(BUILT))):
                text = page.read_text(encoding="utf-8")
                marked = re.findall(r'<a href="([^"]*)" aria-current="page">', text)
                expected = "/" + page.parent.relative_to(BUILT).as_posix() + "/"
                self.assertEqual(marked, [] if expected == "/./" else [expected])

    def test_the_menu_is_written_in_one_place(self):
        # A source page that holds its own menu has a copy that a change of the menu misses.
        for page in SOURCES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                text = page.read_text(encoding="utf-8")
                self.assertNotIn('<nav class="nav"', text)
                self.assertNotIn('<header class="top">', text)


# The steps file that uninstalls on each system: the packaging family of the system.
UNINSTALL = {
    "debian": "apt", "ubuntu": "apt", "rhel": "dnf", "rocky": "dnf", "almalinux": "dnf",
    "amazon": "dnf", "opensuse": "zypper", "alpine": "apk", "freebsd": "pkg",
}


UNINSTALL_DETAILS = re.compile(r'<details id="\w+-uninstall">(.*?)</details>', re.DOTALL)


def shown(name):
    """The code block of a steps file, as a built page holds it."""
    return f"<pre><code>{steps.block(name, STEPS)}</code></pre>"


class TestInstallPage(unittest.TestCase):
    def page(self):
        return INSTALL_PAGE.read_text(encoding="utf-8")

    def systems(self):
        return SYSTEM.findall(self.page())

    def test_it_has_a_section_for_each_system(self):
        self.assertEqual(len(self.systems()), 9)

    def test_each_system_has_the_three_steps_in_order(self):
        for system, body in self.systems():
            with self.subTest(system=system):
                headings = [re.search(r"<h3>(Step \d):", step) for step in STEP.findall(body)]
                self.assertEqual([h.group(1) for h in headings if h], ["Step 1", "Step 2", "Step 3"])

    def test_each_step_has_a_code_block(self):
        for system, body in self.systems():
            steps = STEP.findall(body)
            self.assertEqual(len(steps), 3)
            for number, step in enumerate(steps, 1):
                with self.subTest(system=system, step=number):
                    self.assertIn("<pre><code>", step)

    def test_each_system_shows_the_uninstall_steps_of_its_family_from_the_steps_file(self):
        for system, body in self.systems():
            with self.subTest(system=system):
                family = UNINSTALL[system]
                self.assertEqual(body.count(shown(f"uninstall-{family}")), 1)
                others = [name for name in set(UNINSTALL.values()) - {family}]
                for other in others:
                    self.assertNotIn(shown(f"uninstall-{other}"), body)

    def test_each_system_shows_the_commands_of_a_user_from_the_steps_files(self):
        for system, body in self.systems():
            with self.subTest(system=system):
                self.assertEqual(body.count(shown("user-mode-start")), 1)
                self.assertEqual(body.count(shown("user-mode-use")), 1)

    def test_the_uninstall_steps_in_the_page_source_are_only_markers(self):
        # A copy written by hand drifts from the steps file the packages tests run.
        source = (pages.SITE / "install" / "index.html").read_text(encoding="utf-8")
        found = UNINSTALL_DETAILS.findall(source)
        self.assertEqual(len(found), 9)
        for body in found:
            with self.subTest(body=body[:80]):
                self.assertEqual(body.count("<pre>"), 1)
                self.assertRegex(body, r"<pre><code><!-- steps: uninstall-[a-z]+ --></code></pre>")

    def test_the_page_has_one_chooser_and_it_picks_the_system(self):
        page = self.page()
        self.assertEqual(len(CHOOSER.findall(page)), 1)
        self.assertEqual(page.count('role="group"'), 1)
        self.assertEqual(SYSTEM_BUTTON.findall(page), [system for system, _ in self.systems()])


if __name__ == "__main__":
    unittest.main()


COMPARE_PAGE = BUILT / "compare" / "index.html"
ROW = re.compile(r'<tr><th scope="row">([^<]+)</th>(.*?)</tr>', re.DOTALL)


class TestComparePage(unittest.TestCase):
    def rows(self):
        return ROW.findall(COMPARE_PAGE.read_text(encoding="utf-8"))

    def test_when_to_choose_follows_aims_to_be(self):
        names = [name for name, _ in self.rows()]
        self.assertIn("When to choose this option", names)
        self.assertEqual(names[names.index("Aims to be") + 1], "When to choose this option")

    def test_every_row_has_a_cell_for_each_system(self):
        for name, cells in self.rows():
            with self.subTest(row=name):
                self.assertEqual(cells.count("<td>"), 9)
