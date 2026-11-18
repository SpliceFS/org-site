"""Rules every page of the site keeps."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The pages in the site folder, and the template the change log page is built from.
PAGES = sorted(ROOT.glob("site/**/*.html")) + [ROOT / "scripts" / "changelog-page.html"]
LOGO = re.compile(r'<a class="mark" href="/">')
INSTALL_PAGE = ROOT / "site" / "install" / "index.html"
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
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertRegex(page.read_text(encoding="utf-8"), LOGO)

    def test_the_install_link_of_the_menu_leads_to_the_install_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                found = NAV_INSTALL.search(page.read_text(encoding="utf-8"))
                self.assertIsNotNone(found)
                self.assertEqual(found.group(1), "/install/")


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

    def test_the_page_has_one_chooser_and_it_picks_the_system(self):
        page = self.page()
        self.assertEqual(len(CHOOSER.findall(page)), 1)
        self.assertEqual(page.count('role="group"'), 1)
        self.assertEqual(SYSTEM_BUTTON.findall(page), [system for system, _ in self.systems()])


if __name__ == "__main__":
    unittest.main()


COMPARE_PAGE = ROOT / "site" / "compare" / "index.html"
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
